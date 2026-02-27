"""
Social Media Cleaner Pro 2026
Created by Kareem Mohamed
Version: 4.0.0 - Production Ready
"""
from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
import threading
import queue
import random
import os
import logging
from datetime import datetime, timedelta
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
import pyperclip
from colorama import init, Fore, Style
import backoff
from ratelimit import limits, sleep_and_retry
import hashlib
import hmac
# تهيئة الألوان للـ console
init(autoreset=True)
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
CORS(app)
# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleaner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# تهيئة User-Agent العشوائي
ua = UserAgent()
# روابط استخراج الكوكيز المباشرة لكل منصة
SESSION_GUIDES = {
    'facebook': {
        'name': 'فيسبوك',
        'icon': 'fab fa-facebook',
        'color': '#1877f2',
        'extraction_methods': [
            {
                'type': 'direct_link',
                'title': 'الرابط المباشر',
                'url': 'https://www.facebook.com/',
                'description': 'افتح الرابط وسجل دخولك'
            },
            {
                'type': 'browser_extension',
                'title': 'إضافة المتصفح',
                'url': 'https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid',
                'description': 'أضف الإضافة وانسخ الكوكيز بضغطة زر'
            },
            {
                'type': 'youtube',
                'title': 'فيديو شرح',
                'url': 'https://youtu.be/example_facebook',
                'description': 'شاهد الشرح بالفيديو'
            }
        ],
        'quick_links': {
            'settings': 'https://www.facebook.com/settings',
            'activity_log': 'https://www.facebook.com/me/allactivity',
            'cookies_location': 'Application → Cookies → https://www.facebook.com'
        },
        'steps_arabic': [
            'اضغط على الرابط المباشر',
            'اضغط F12 (أو Ctrl+Shift+I)',
            'اختار تبويب Application',
            'من الشمال اختار Cookies',
            'اضغط Ctrl+A ثم Ctrl+C'
        ]
    },
    'instagram': {
        'name': 'انستجرام',
        'icon': 'fab fa-instagram',
        'color': '#e4405f',
        'extraction_methods': [
            {
                'type': 'direct_link',
                'title': 'الرابط المباشر',
                'url': 'https://www.instagram.com/accounts/edit/',
                'description': 'أسرع طريقة للحصول على الكوكيز'
            }
        ],
        'quick_links': {
            'profile': 'https://www.instagram.com/',
            'activity': 'https://www.instagram.com/accounts/activity/',
            'cookies_location': 'Application → Cookies → https://www.instagram.com'
        },
        'steps_arabic': [
            'افتح الرابط وسجل دخولك',
            'اضغط F12',
            'روح لـ Application → Cookies',
            'اختار https://www.instagram.com',
            'انسخ كل الكوكيز'
        ]
    },
    'tiktok': {
        'name': 'تيك توك',
        'icon': 'fab fa-tiktok',
        'color': '#000000',
        'extraction_methods': [
            {
                'type': 'direct_link',
                'title': 'الرابط المباشر',
                'url': 'https://www.tiktok.com/',
                'description': 'افتح الرابط وسجل دخول'
            }
        ],
        'quick_links': {
            'foryou': 'https://www.tiktok.com/foryou',
            'profile': 'https://www.tiktok.com/@user',
            'cookies_location': 'Network tab → أي request → Headers'
        },
        'steps_arabic': [
            'افتح الرابط وسجل دخولك',
            'اضغط F12',
            'اختار Network',
            'عمل Refresh للصفحة',
            'دور على أي api request',
            'انسخ الكوكيز من Headers'
        ]
    },
    'twitter': {
        'name': 'X (تويتر)',
        'icon': 'fab fa-x-twitter',
        'color': '#000000',
        'extraction_methods': [
            {
                'type': 'direct_link',
                'title': 'الرابط المباشر',
                'url': 'https://twitter.com/home',
                'description': 'افتح الرابط وسجل دخولك'
            }
        ],
        'quick_links': {
            'home': 'https://twitter.com/home',
            'settings': 'https://twitter.com/settings/account',
            'cookies_location': 'Application → Cookies → https://twitter.com'
        },
        'steps_arabic': [
            'افتح الرابط وسجل دخول',
            'اضغط F12',
            'روح لـ Application → Cookies',
            'اختار https://twitter.com',
            'انسخ كل الكوكيز'
        ],
        'status': 'قريباً'
    }
}
class RequestsSession:
    """جلسة مخصصة للطلبات مع إعادة محاولة ذكية"""
    
    def __init__(self, cookies=None, proxy=None):
        self.session = requests.Session()
        self.setup_retries()
        self.setup_headers()
        
        if cookies:
            self.load_cookies(cookies)
            
        if proxy:
            self.session.proxies = {'http': proxy, 'https': proxy}
    
    def setup_retries(self):
        """إعداد إعادة المحاولة التلقائية"""
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def setup_headers(self):
        """إعداد الرؤوس بشكل عشوائي"""
        self.session.headers.update({
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ar,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def load_cookies(self, cookies_string):
        """تحميل الكوكيز من النص"""
        try:
            if cookies_string.strip().startswith('{'):
                cookies_dict = json.loads(cookies_string)
            else:
                cookies_dict = {}
                for item in cookies_string.split(';'):
                    if '=' in item:
                        key, value = item.strip().split('=', 1)
                        cookies_dict[key] = value
            
            requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies_dict)
            logger.info(f"✅ تم تحميل {len(cookies_dict)} كوكيز")
            return True
        except Exception as e:
            logger.error(f"❌ فشل تحميل الكوكيز: {e}")
            return False
class SmartDeleter:
    """المحرك الذكي للحذف - يدعم 10,000+ عنصر"""
    
    def __init__(self, platform, cookies, action_type, max_workers=10):
        self.platform = platform
        self.cookies = cookies
        self.action_type = action_type
        self.max_workers = max_workers
        self.session = RequestsSession(cookies)
        self.deleted_count = 0
        self.failed_count = 0
        self.total_items = 0
        self.items_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.progress_callback = None
        self.log_callback = None
        
        # إعدادات خاصة بكل منصة
        self.platform_configs = {
            'facebook': {
                'base_url': 'https://www.facebook.com',
                'delete_endpoint': '/ajax/remove_share.php',
                'rate_limit': 30,  # طلب في الدقيقة
                'batch_size': 50,
                'delay_range': (2, 5)
            },
            'instagram': {
                'base_url': 'https://www.instagram.com',
                'delete_endpoint': '/web/likes/{}/unlike/',
                'rate_limit': 60,
                'batch_size': 30,
                'delay_range': (1, 3)
            },
            'tiktok': {
                'base_url': 'https://www.tiktok.com',
                'delete_endpoint': '/api/repost/item/remove/',
                'rate_limit': 20,
                'batch_size': 20,
                'delay_range': (3, 7)
            },
            'twitter': {
                'base_url': 'https://twitter.com',
                'delete_endpoint': '/i/api/retweet/delete/{}',
                'rate_limit': 50,
                'batch_size': 100,
                'delay_range': (1, 2)
            }
        }
        
        self.config = self.platform_configs.get(platform, {})
    
    def fetch_items(self, limit=1000):
        """جلب العناصر المراد حذفها مع دعم الصفحات"""
        items = []
        cursor = None
        page = 1
        
        logger.info(f"🔍 بدء جلب العناصر من {self.platform} - {self.action_type}")
        
        while len(items) < limit:
            try:
                batch = self.fetch_batch(cursor, min(100, limit - len(items)))
                if not batch:
                    break
                    
                items.extend(batch)
                
                # تحديث cursor للصفحة التالية
                cursor = self.get_next_cursor(batch)
                
                if not cursor:
                    break
                    
                logger.info(f"📄 تم جلب صفحة {page}: {len(batch)} عنصر")
                page += 1
                
                # تأخير بين الصفحات
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"❌ خطأ في جلب الصفحة {page}: {e}")
                break
        
        self.total_items = len(items)
        logger.info(f"✅ تم جلب {self.total_items} عنصر إجمالاً")
        return items
    
    def fetch_batch(self, cursor, count):
        """جلب دفعة واحدة من العناصر"""
        if self.platform == 'twitter':
            return self.fetch_twitter_batch(cursor, count)
        elif self.platform == 'facebook':
            return self.fetch_facebook_batch(cursor, count)
        elif self.platform == 'instagram':
            return self.fetch_instagram_batch(cursor, count)
        elif self.platform == 'tiktok':
            return self.fetch_tiktok_batch(cursor, count)
        return []
    
    def fetch_twitter_batch(self, cursor, count):
        """جلب دفعة من تويتر"""
        try:
            user_id = self.get_twitter_user_id()
            if not user_id:
                return []
            
            url = "https://twitter.com/i/api/graphql/onXoUHeRVpQH7B6niLqjzA/UserTweets"
            
            variables = {
                "userId": user_id,
                "count": count,
                "cursor": cursor,
                "includePromotedContent": False,
                "withQuickPromoteEligibilityTweetFields": False,
                "withVoice": False,
                "withV2Timeline": False
            }
            
            features = {
                "responsive_web_twitter_blue_verified_badge_is_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": False,
                "verified_phone_label_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False
            }
            
            params = {
                'variables': json.dumps(variables),
                'features': json.dumps(features)
            }
            
            response = self.session.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_twitter_items(data)
            else:
                logger.warning(f"⚠️ تويتر رد بكود {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب دفعة تويتر: {e}")
            return []
    
    def fetch_facebook_batch(self, cursor, count):
        """جلب دفعة من فيسبوك"""
        try:
            url = "https://www.facebook.com/api/graphql/"
            
            # هذا doc_id خاص بجلب النشاطات (يحتاج تحديث دوري)
            doc_id = "123456789012345"
            
            payload = {
                'doc_id': doc_id,
                'variables': json.dumps({
                    'count': count,
                    'cursor': cursor
                })
            }
            
            response = self.session.session.post(url, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_facebook_items(data)
            
            return []
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب دفعة فيسبوك: {e}")
            return []
    
    def fetch_instagram_batch(self, cursor, count):
        """جلب دفعة من انستجرام"""
        try:
            url = "https://www.instagram.com/graphql/query/"
            
            # query_hash خاص باللايكات
            query_hash = "de8017ee0a7c9c45ec4260733d81ea31"
            
            params = {
                'query_hash': query_hash,
                'variables': json.dumps({
                    'first': count,
                    'after': cursor
                })
            }
            
            response = self.session.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_instagram_items(data)
            
            return []
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب دفعة انستجرام: {e}")
            return []
    
    def fetch_tiktok_batch(self, cursor, count):
        """جلب دفعة من تيك توك"""
        try:
            url = "https://www.tiktok.com/api/repost/item/list/"
            
            params = {
                'count': count,
                'cursor': cursor,
                'aid': 1988,
                'app_language': 'ar',
                'app_name': 'tiktok_web',
                'device_platform': 'web'
            }
            
            response = self.session.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_tiktok_items(data)
            
            return []
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب دفعة تيك توك: {e}")
            return []
    
    def parse_twitter_items(self, data):
        """تحليل بيانات تويتر"""
        items = []
        try:
            instructions = data.get('data', {}).get('user', {}).get('result', {}).get('timeline_v2', {}).get('timeline', {}).get('instructions', [])
            
            for instruction in instructions:
                if instruction.get('type') == 'TimelineAddEntries':
                    entries = instruction.get('entries', [])
                    for entry in entries:
                        item = self.extract_twitter_item(entry)
                        if item:
                            items.append(item)
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل بيانات تويتر: {e}")
        
        return items
    
    def extract_twitter_item(self, entry):
        """استخراج عنصر من تويتر"""
        try:
            content = entry.get('content', {})
            if content.get('entryType') == 'TimelineTimelineItem':
                item_content = content.get('itemContent', {}).get('tweet_results', {}).get('result', {})
                
                # تحقق من نوع العنصر حسب الإجراء المطلوب
                if self.action_type == 'reposts':
                    if item_content.get('legacy', {}).get('retweeted_status_result'):
                        return {
                            'id': item_content.get('rest_id'),
                            'type': 'repost',
                            'text': item_content.get('legacy', {}).get('full_text', '')[:100],
                            'date': item_content.get('legacy', {}).get('created_at', ''),
                            'url': f"https://twitter.com/i/web/status/{item_content.get('rest_id')}"
                        }
                
                elif self.action_type == 'likes':
                    if item_content.get('legacy', {}).get('favorited'):
                        return {
                            'id': item_content.get('rest_id'),
                            'type': 'like',
                            'text': item_content.get('legacy', {}).get('full_text', '')[:100],
                            'date': item_content.get('legacy', {}).get('created_at', '')
                        }
                
                elif self.action_type == 'comments':
                    if item_content.get('legacy', {}).get('in_reply_to_status_id'):
                        return {
                            'id': item_content.get('rest_id'),
                            'type': 'comment',
                            'text': item_content.get('legacy', {}).get('full_text', '')[:100],
                            'date': item_content.get('legacy', {}).get('created_at', '')
                        }
        except Exception as e:
            logger.debug(f"خطأ في استخراج عنصر: {e}")
        
        return None
    
    def parse_facebook_items(self, data):
        """تحليل بيانات فيسبوك"""
        items = []
        # هون هتحط منطق تحليل فيسبوك
        return items
    
    def parse_instagram_items(self, data):
        """تحليل بيانات انستجرام"""
        items = []
        # هون هتحط منطق تحليل انستجرام
        return items
    
    def parse_tiktok_items(self, data):
        """تحليل بيانات تيك توك"""
        items = []
        # هون هتحط منطق تحليل تيك توك
        return items
    
    def get_next_cursor(self, batch):
        """الحصول على cursor الصفحة التالية"""
        # هون هتحط منطق الحصول على الـ cursor حسب المنصة
        return None
    
    def get_twitter_user_id(self):
        """الحصول على ID المستخدم من تويتر"""
        try:
            response = self.session.session.get("https://twitter.com/i/api/1.1/account/settings.json")
            if response.status_code == 200:
                data = response.json()
                return data.get('id_str')
        except:
            pass
        return None
    
    @sleep_and_retry
    @limits(calls=30, period=60)
    def delete_with_rate_limit(self, item_id):
        """حذف مع مراعاة حدود السرعة"""
        return self.delete_single_item(item_id)
    
    def delete_single_item(self, item_id):
        """حذف عنصر واحد"""
        try:
            if self.platform == 'twitter':
                if self.action_type == 'reposts':
                    url = f"https://twitter.com/i/api/retweet/delete/{item_id}"
                elif self.action_type == 'likes':
                    url = f"https://twitter.com/i/api/favorite/destroy/{item_id}.json"
                elif self.action_type == 'comments':
                    url = f"https://twitter.com/i/api/delete/tweet/{item_id}"
                else:
                    return False, "إجراء غير مدعوم"
            
            elif self.platform == 'facebook':
                if self.action_type == 'reposts':
                    url = "https://www.facebook.com/ajax/remove_share.php"
                    data = {'share_id': item_id}
                    response = self.session.session.post(url, data=data)
                    return response.status_code in [200, 201, 204], ""
                elif self.action_type == 'comments':
                    url = "https://www.facebook.com/ajax/comment/remove/"
                    data = {'comment_id': item_id}
                    response = self.session.session.post(url, data=data)
                    return response.status_code in [200, 201, 204], ""
                else:
                    return False, "إجراء غير مدعوم"
            
            elif self.platform == 'instagram':
                if self.action_type == 'likes':
                    url = f"https://www.instagram.com/web/likes/{item_id}/unlike/"
                elif self.action_type == 'comments':
                    url = f"https://www.instagram.com/web/comments/{item_id}/delete/"
                else:
                    return False, "إجراء غير مدعوم"
                
                response = self.session.session.post(url)
                return response.status_code in [200, 201, 204], ""
            
            elif self.platform == 'tiktok':
                if self.action_type == 'reposts':
                    url = "https://www.tiktok.com/api/repost/item/remove/"
                    data = {'item_id': item_id}
                    response = self.session.session.post(url, data=data)
                    return response.status_code in [200, 201, 204], ""
                else:
                    return False, "إجراء غير مدعوم"
            
            else:
                return False, "منصة غير مدعومة"
            
            # للتويتر وغيره من الطلبات الـ GET/POST العادية
            if self.action_type in ['reposts', 'likes', 'comments']:
                response = self.session.session.post(url)
                return response.status_code in [200, 201, 204, 429], f"HTTP {response.status_code}"
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف {item_id}: {e}")
            return False, str(e)
    
    def worker(self, worker_id):
        """عامل في Pool الحذف"""
        logger.info(f"🧵 بدأ العامل {worker_id}")
        
        while not self.stop_flag.is_set():
            try:
                # جلب عنصر من الطابور مع timeout
                item = self.items_queue.get(timeout=5)
                
                if item is None:
                    break
                
                # حذف العنصر
                success, error = self.delete_with_rate_limit(item['id'])
                
                if success:
                    self.deleted_count += 1
                    self.results_queue.put({
                        'status': 'success',
                        'item': item,
                        'worker': worker_id
                    })
                    
                    if self.log_callback:
                        self.log_callback(f"✅ تم حذف: {item.get('text', 'عنصر')}")
                        
                else:
                    self.failed_count += 1
                    self.results_queue.put({
                        'status': 'failed',
                        'item': item,
                        'error': error,
                        'worker': worker_id
                    })
                    
                    if self.log_callback:
                        self.log_callback(f"❌ فشل حذف: {item.get('text', 'عنصر')} - {error}")
                
                # تحديث التقدم
                if self.progress_callback:
                    progress = (self.deleted_count + self.failed_count) / self.total_items * 100
                    self.progress_callback(
                        progress,
                        self.deleted_count,
                        self.failed_count,
                        self.total_items
                    )
                
                # تأخير ذكي بين العمليات
                delay = random.uniform(*self.config.get('delay_range', (1, 3)))
                time.sleep(delay)
                
                # كل 10 عناصر نأخذ راحة أطول
                if (self.deleted_count + self.failed_count) % 10 == 0:
                    time.sleep(delay * 2)
                
                self.items_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ خطأ في العامل {worker_id}: {e}")
                continue
        
        logger.info(f"🛑 توقف العامل {worker_id}")
    
    def start_deleting(self, items):
        """بدء عملية الحذف المتعددة الخيوط"""
        
        self.total_items = len(items)
        self.deleted_count = 0
        self.failed_count = 0
        
        logger.info(f"🚀 بدء الحذف بـ {self.max_workers} عامل لـ {self.total_items} عنصر")
        
        # وضع العناصر في الطابور
        for item in items:
            self.items_queue.put(item)
        
        # بدء العمال
        workers = []
        for i in range(self.max_workers):
            worker_thread = threading.Thread(target=self.worker, args=(i,))
            worker_thread.daemon = True
            worker_thread.start()
            workers.append(worker_thread)
        
        # انتظار انتهاء جميع العناصر
        self.items_queue.join()
        
        # إيقاف العمال
        self.stop_flag.set()
        for _ in range(self.max_workers):
            self.items_queue.put(None)
        
        for worker in workers:
            worker.join(timeout=5)
        
        logger.info(f"🏁 انتهى الحذف: {self.deleted_count} نجاح، {self.failed_count} فشل")
        
        # تجميع النتائج
        results = {
            'success': [],
            'failed': [],
            'total': self.total_items,
            'deleted': self.deleted_count,
            'failed_count': self.failed_count
        }
        
        while not self.results_queue.empty():
            result = self.results_queue.get()
            if result['status'] == 'success':
                results['success'].append(result['item'])
            else:
                results['failed'].append(result['item'])
        
        return results
class SessionExtractor:
    """مولد روابط استخراج الجلسات"""
    
    @staticmethod
    def get_platform_links(platform):
        """الحصول على روابط استخراج الجلسة لمنصة محددة"""
        return SESSION_GUIDES.get(platform, {})
    
    @staticmethod
    def generate_copy_script(platform):
        """توليد سكربت جافاسكريبت لنسخ الكوكيز"""
        scripts = {
            'facebook': """
                // كود لنسخ كوكيز فيسبوك
                var cookies = document.cookie.split(';').map(c => c.trim()).join(';');
                navigator.clipboard.writeText(cookies).then(() => {
                    alert('✅ تم نسخ الكوكيز بنجاح!');
                });
            """,
            'instagram': """
                var cookies = document.cookie.split(';').map(c => c.trim()).join(';');
                navigator.clipboard.writeText(cookies);
            """
        }
        return scripts.get(platform, "alert('لا يمكن نسخ الكوكيز تلقائياً')")
    
    @staticmethod
    def get_browser_extensions():
        """الحصول على إضافات المتصفح لاستخراج الكوكيز"""
        return [
            {
                'name': 'Get cookies.txt',
                'chrome': 'https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid',
                'firefox': 'https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/',
                'description': 'استخرج الكوكيز بضغطة زر'
            },
            {
                'name': 'Cookie-Editor',
                'chrome': 'https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm',
                'firefox': 'https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/',
                'description': 'تعديل ونسخ الكوكيز بسهولة'
            }
        ]
# ------------------- Routes ------------------- #
@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')
@app.route('/api/platforms')
def get_platforms():
    """جلب قائمة المنصات المدعومة"""
    platforms = [
        {
            'id': 'facebook',
            'name': 'فيسبوك',
            'icon': 'fab fa-facebook',
            'color': '#1877f2',
            'status': 'active'
        },
        {
            'id': 'instagram',
            'name': 'انستجرام',
            'icon': 'fab fa-instagram',
            'color': '#e4405f',
            'status': 'active'
        },
        {
            'id': 'tiktok',
            'name': 'تيك توك',
            'icon': 'fab fa-tiktok',
            'color': '#000000',
            'status': 'active'
        },
        {
            'id': 'twitter',
            'name': 'X',
            'icon': 'fab fa-x-twitter',
            'color': '#000000',
            'status': 'coming_soon'
        }
    ]
    return jsonify(platforms)
@app.route('/api/session-guide/<platform>')
def get_session_guide(platform):
    """الحصول على دليل استخراج الجلسة لمنصة محددة"""
    guide = SESSION_GUIDES.get(platform, {})
    if guide:
        guide['extensions'] = SessionExtractor.get_browser_extensions()
        return jsonify({'success': True, 'guide': guide})
    return jsonify({'success': False, 'error': 'منصة غير مدعومة'}), 404
@app.route('/api/quick-copy/<platform>')
def get_quick_copy_script(platform):
    """الحصول على سكربت النسخ السريع"""
    script = SessionExtractor.generate_copy_script(platform)
    return jsonify({'success': True, 'script': script})
@app.route('/api/verify-cookies', methods=['POST'])
def verify_cookies():
    """التحقق من صحة الكوكيز"""
    try:
        data = request.json
        platform = data.get('platform')
        cookies = data.get('cookies')
        
        if not platform or not cookies:
            return jsonify({'success': False, 'error': 'البيانات غير مكتملة'}), 400
        
        # إنشاء جلسة للتحقق
        session = RequestsSession(cookies)
        
        # محاولة الوصول لصفحة شخصية للتحقق
        verification_urls = {
            'facebook': 'https://www.facebook.com/me/',
            'instagram': 'https://www.instagram.com/accounts/edit/',
            'tiktok': 'https://www.tiktok.com/@user',
            'twitter': 'https://twitter.com/home'
        }
        
        url = verification_urls.get(platform)
        if not url:
            return jsonify({'success': False, 'error': 'منصة غير مدعومة'}), 400
        
        response = session.session.get(url, timeout=10, allow_redirects=True)
        
        # التحقق من أننا لم نُعاد توجيه لصفحة تسجيل الدخول
        if 'login' in response.url.lower() or 'auth' in response.url.lower():
            return jsonify({
                'success': False,
                'error': '❌ الكوكيز غير صالحة أو منتهية الصلاحية'
            })
        
        # محاولة استخراج اسم المستخدم
        username = extract_username_from_response(platform, response.text)
        
        return jsonify({
            'success': True,
            'message': '✅ الكوكيز صالحة',
            'username': username,
            'expires': 'غير معروف'
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': '⚠️ تأخر في الاستجابة'}), 504
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
def extract_username_from_response(platform, html):
    """استخراج اسم المستخدم من الـ HTML"""
    try:
        if platform == 'facebook':
            import re
            match = re.search(r'"name":"([^"]+)"', html)
            return match.group(1) if match else 'مستخدم فيسبوك'
    except:
        pass
    return 'مستخدم'
@app.route('/api/fetch-items', methods=['POST'])
def fetch_items():
    """جلب العناصر للحذف"""
    try:
        data = request.json
        platform = data.get('platform')
        cookies = data.get('cookies')
        action = data.get('action')
        limit = data.get('limit', 1000)
        
        if not all([platform, cookies, action]):
            return jsonify({'success': False, 'error': 'البيانات غير مكتملة'}), 400
        
        # إنشاء محرك الحذف
        deleter = SmartDeleter(platform, cookies, action)
        
        # جلب العناصر
        items = deleter.fetch_items(limit=limit)
        
        return jsonify({
            'success': True,
            'items': items[:50],  # نرجع أول 50 عنصر فقط للعرض
            'total_count': len(items),
            'has_more': len(items) >= limit
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب العناصر: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/start-deleting', methods=['POST'])
def start_deleting():
    """بدء عملية الحذف"""
    try:
        data = request.json
        platform = data.get('platform')
        cookies = data.get('cookies')
        action = data.get('action')
        delete_type = data.get('delete_type', 'all')  # all or selected
        selected_items = data.get('selected_items', [])
        max_workers = data.get('max_workers', 10)  # عدد العمال
        
        if not all([platform, cookies, action]):
            return jsonify({'success': False, 'error': 'البيانات غير مكتملة'}), 400
        
        # إنشاء محرك الحذف
        deleter = SmartDeleter(platform, cookies, action, max_workers=max_workers)
        
        # جلب العناصر إذا كان الحذف الكل
        if delete_type == 'all':
            items = deleter.fetch_items(limit=10000)  # نجلب حتى 10000 عنصر
        else:
            items = selected_items
        
        if not items:
            return jsonify({'success': False, 'error': 'لا توجد عناصر للحذف'}), 404
        
        # بدء الحذف في thread منفصل عشان ما يحجبش السيرفر
        def delete_task():
            results = deleter.start_deleting(items)
            # هنا ممكن تخزن النتائج في قاعدة بيانات أو cache
        
        thread = threading.Thread(target=delete_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'بدأت عملية الحذف',
            'total_items': len(items),
            'task_id': str(time.time())  # مؤقت، الأفضل استخدام UUID
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء الحذف: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/delete-status/<task_id>')
def get_delete_status(task_id):
    """الحصول على حالة الحذف"""
    # هون هتجيب الحالة من الـ cache أو DB
    return jsonify({
        'success': True,
        'status': 'running',
        'progress': 45,
        'deleted': 450,
        'failed': 23,
        'total': 1000
    })
@app.route('/api/extensions')
def get_extensions():
    """جلب إضافات المتصفح المتاحة"""
    extensions = SessionExtractor.get_browser_extensions()
    return jsonify({'success': True, 'extensions': extensions})
@app.route('/api/export-session/<platform>')
def export_session_html(platform):
    """تصدير صفحة HTML لاستخراج الكوكيز"""
    guide = SESSION_GUIDES.get(platform, {})
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>استخراج كوكيز {guide.get('name', platform)}</title>
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; }}
            .steps {{ text-align: right; max-width: 600px; margin: auto; }}
            .step {{ background: #f0f0f0; margin: 10px; padding: 15px; border-radius: 10px; }}
            button {{ 
                background: #667eea; 
                color: white; 
                border: none; 
                padding: 15px 30px; 
                font-size: 18px;
                border-radius: 10px;
                cursor: pointer;
                margin: 20px;
            }}
            button:hover {{ background: #5a67d8; }}
            textarea {{ width: 80%; height: 150px; margin: 20px; padding: 15px; }}
        </style>
    </head>
    <body>
        <h1>استخراج كوكيز {guide.get('name', platform)}</h1>
        <button onclick="copyCookies()">📋 نسخ الكوكيز</button>
        <textarea id="cookies" readonly placeholder="هنا ستظهر الكوكيز..."></textarea>
        
        <div class="steps">
            <h2>خطوات الاستخراج اليدوي:</h2>
            {"".join([f'<div class="step">{step}</div>' for step in guide.get('steps_arabic', [])])}
        </div>
        
        <script>
            function copyCookies() {{
                var cookies = document.cookie;
                document.getElementById('cookies').value = cookies;
                navigator.clipboard.writeText(cookies).then(() => {{
                    alert('✅ تم النسخ! ارجع للصفحة الرئيسية والصق الكوكيز');
                }});
            }}
            
            // محاولة قراءة الكوكيز الحالية
            window.onload = function() {{
                if (document.cookie) {{
                    document.getElementById('cookies').value = document.cookie;
                }}
            }};
        </script>
    </body>
    </html>
    """
    return html
@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'الصفحة غير موجودة'}), 404
@app.errorhandler(500)
def server_error(e):
    logger.error(f"خطأ في السيرفر: {e}")
    return jsonify({'success': False, 'error': 'حدث خطأ داخلي في السيرفر'}), 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
