"""
18comic 頁面爬取模組

使用 Playwright 模擬瀏覽器訪問，提取圖片列表並下載。
"""
import random
import re
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Page, Browser
import httpx


# 常用 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


@dataclass
class ImageInfo:
    """圖片資訊"""
    url: str
    photo_id: str
    index: int


@dataclass
class AlbumInfo:
    """相簿資訊"""
    aid: int
    title: str
    images: list[ImageInfo]


def get_random_user_agent() -> str:
    """取得隨機 User-Agent"""
    return random.choice(USER_AGENTS)


def extract_aid_from_url(url: str) -> int:
    """
    從 URL 提取相簿 ID。
    
    Args:
        url: 頁面 URL（如 https://18comic.vip/photo/1223474）
    
    Returns:
        int: 相簿 ID
    """
    match = re.search(r'/photo/(\d+)', url)
    if match:
        return int(match.group(1))
    raise ValueError(f"無法從 URL 提取 aid: {url}")


def extract_photo_id_from_url(url: str) -> str:
    """
    從圖片 URL 提取 photo_id。
    
    Args:
        url: 圖片 URL（如 https://cdn-msp.18comic.vip/media/photos/1223474/00001.webp）
    
    Returns:
        str: photo_id（如 "00001"）
    """
    match = re.search(r'/(\d+)\.\w+$', url)
    if match:
        return match.group(1)
    raise ValueError(f"無法從 URL 提取 photo_id: {url}")


def scrape_album(url: str, headless: bool = True) -> AlbumInfo:
    """
    使用 Playwright 爬取相簿頁面，提取圖片列表。
    
    Args:
        url: 相簿頁面 URL
        headless: 是否使用無頭模式
    
    Returns:
        AlbumInfo: 相簿資訊（包含所有圖片 URL）
    """
    aid = extract_aid_from_url(url)
    
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={"width": 1920, "height": 1080},
        )
        
        page: Page = context.new_page()
        
        # 設置額外的 headers
        page.set_extra_http_headers({
            "Referer": "https://18comic.vip/",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        
        # 訪問頁面（使用 domcontentloaded 避免等待所有資源）
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # 等待圖片選擇器出現
        try:
            page.wait_for_selector("img.lazy_img, img[id^='album_photo_'], .scramble-page img", timeout=15000)
        except Exception:
            # 若選擇器等待失敗，繼續嘗試
            pass
        
        # 捲動頁面以載入所有圖片（懶加載）
        _scroll_page(page)
        
        # 提取頁面標題
        title = page.title()
        
        # 提取所有圖片 URL
        images = _extract_images(page, aid)
        
        browser.close()
    
    return AlbumInfo(aid=aid, title=title, images=images)


def _scroll_page(page: Page, scroll_times: int = 10, delay_ms: int = 500) -> None:
    """
    捲動頁面以觸發懶加載圖片。
    
    Args:
        page: Playwright 頁面物件
        scroll_times: 捲動次數
        delay_ms: 每次捲動後的等待時間（毫秒）
    """
    for _ in range(scroll_times):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(delay_ms)


def _extract_images(page: Page, aid: int) -> list[ImageInfo]:
    """
    從頁面提取圖片資訊。
    
    Args:
        page: Playwright 頁面物件
        aid: 相簿 ID
    
    Returns:
        list[ImageInfo]: 圖片資訊列表
    """
    # 使用 JavaScript 提取圖片資訊
    image_data = page.evaluate("""
        () => {
            const images = [];
            // 嘗試多種選擇器
            const selectors = [
                'img.lazy_img[data-original]',
                'img[id^="album_photo_"]',
                '.scramble-page img[data-original]',
                '.panel-body img[data-original]'
            ];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                for (const img of elements) {
                    const url = img.getAttribute('data-original') || img.src;
                    if (url && url.includes('/media/photos/')) {
                        images.push(url);
                    }
                }
                if (images.length > 0) break;
            }
            
            // 去重並保持順序
            return [...new Set(images)];
        }
    """)
    
    result = []
    for idx, url in enumerate(image_data):
        try:
            photo_id = extract_photo_id_from_url(url)
            result.append(ImageInfo(url=url, photo_id=photo_id, index=idx + 1))
        except ValueError:
            continue
    
    return result


def download_image(url: str, referer: str = "https://18comic.vip/") -> bytes:
    """
    下載圖片。
    
    Args:
        url: 圖片 URL
        referer: Referer header（必須包含 18comic.vip 域名）
    
    Returns:
        bytes: 圖片二進位資料
    """
    headers = {
        "User-Agent": get_random_user_agent(),
        "Referer": referer,
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    }
    
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.content
