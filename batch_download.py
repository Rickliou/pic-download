#!/usr/bin/env python3
"""
18comic 相簿批量下載工具

從相簿列表頁面提取所有章節連結，依序下載並生成 PDF。
"""
import argparse
import re
import sys
import time
import random
from pathlib import Path
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, Page, Browser
from descrambler import restore_image
from scraper import get_random_user_agent, download_image, _scroll_page
from to_pdf import images_to_pdf


def sanitize_filename(name: str) -> str:
    """
    清理檔名/目錄名稱，防止路徑遍歷攻擊。
    
    Args:
        name: 原始名稱
    
    Returns:
        str: 清理後的安全名稱
    """
    # 移除路徑遍歷符號
    name = name.replace('..', '')
    # 移除所有斜線
    name = name.replace('/', '_').replace('\\', '_')
    # 移除特殊字元
    name = re.sub(r'[<>:"|?*]', '_', name)
    # 移除開頭的點和空格
    name = name.lstrip('. ')
    # 移除結尾的點和空格
    name = name.rstrip('. ')
    # 限制長度
    name = name[:200] if name else "untitled"
    # 如果清理後為空，返回預設值
    return name if name else "untitled"


@dataclass
class ChapterInfo:
    """章節資訊"""
    title: str
    url: str
    photo_id: str
    episode_num: int  # 話數編號


def extract_album_chapters(url: str, headless: bool = True) -> tuple[str, list[ChapterInfo]]:
    """
    從相簿頁面提取所有章節連結。
    
    Args:
        url: 相簿頁面 URL（如 https://18comic.vip/album/1223474/）
        headless: 是否使用無頭模式
    
    Returns:
        tuple[str, list[ChapterInfo]]: (相簿標題, 章節列表)
    """
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={"width": 1920, "height": 1080},
        )
        
        page: Page = context.new_page()
        page.set_extra_http_headers({
            "Referer": "https://18comic.vip/",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        
        # 訪問頁面
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # 等待並捲動以載入所有內容
        page.wait_for_timeout(2000)
        _scroll_page(page, scroll_times=5, delay_ms=500)
        
        # 提取相簿標題
        album_title = page.evaluate("""
            () => {
                const h1 = document.querySelector('h1');
                return h1 ? h1.textContent.trim() : 'Unknown';
            }
        """)
        
        # 提取所有章節連結
        raw_chapters = page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href*="/photo/"]'));
                const seen = new Set();
                const results = [];
                
                for (const a of links) {
                    const href = a.getAttribute('href');
                    const text = a.textContent.trim();
                    
                    // 跳過重複連結
                    if (seen.has(href)) continue;
                    seen.add(href);
                    
                    // 跳過空文字或太短的連結（可能是按鈕）
                    if (!text || text.length < 2) continue;
                    
                    results.push({ text, href });
                }
                
                return results;
            }
        """)
        
        browser.close()
    
    # 解析章節資訊
    chapters = []
    episode_counter = 0
    
    for item in raw_chapters:
        text = item["text"]
        href = item["href"]
        
        # 過濾休刊公告
        if "休刊" in text or "公告" in text:
            print(f"  ⏭️  跳過: {text}")
            continue
        
        # 提取 photo_id
        match = re.search(r'/photo/(\d+)', href)
        if not match:
            continue
        
        photo_id = match.group(1)
        episode_counter += 1
        
        # 建立完整 URL
        full_url = f"https://18comic.vip/photo/{photo_id}"
        
        chapters.append(ChapterInfo(
            title=text,
            url=full_url,
            photo_id=photo_id,
            episode_num=episode_counter,
        ))
    
    return album_title, chapters


def download_chapter_images(
    chapter: ChapterInfo,
    output_dir: Path,
    headless: bool = True,
    delay: float = 0.3,
) -> Path:
    """
    下載單一章節的所有圖片。
    
    Args:
        chapter: 章節資訊
        output_dir: 輸出目錄
        headless: 是否使用無頭模式
        delay: 下載間隔
    
    Returns:
        Path: 圖片儲存目錄
    """
    from scraper import scrape_album
    
    # 建立章節目錄
    chapter_dir = output_dir / f"ep{chapter.episode_num:03d}_{chapter.photo_id}"
    chapter_dir.mkdir(exist_ok=True)
    
    print(f"\n📖 第 {chapter.episode_num} 話: {chapter.title}")
    print(f"   URL: {chapter.url}")
    
    # 爬取圖片列表
    album = scrape_album(chapter.url, headless=headless)
    print(f"   找到 {len(album.images)} 張圖片")
    
    # 下載並還原每張圖片
    for img_info in album.images:
        output_filename = f"{img_info.index:04d}_{img_info.photo_id}.webp"
        output_path = chapter_dir / output_filename
        
        # 檢查是否已存在
        if output_path.exists():
            continue
        
        try:
            # 下載並還原
            scrambled_data = download_image(img_info.url, referer=chapter.url)
            restored_img = restore_image(scrambled_data, album.aid, img_info.photo_id)
            restored_img.save(output_path)
            print(f"   ✓ {img_info.photo_id}")
        except Exception as e:
            print(f"   ✗ {img_info.photo_id}: {e}")
        
        time.sleep(delay + random.uniform(0, 0.2))
    
    return chapter_dir


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="18comic 相簿批量下載工具",
    )
    parser.add_argument(
        "album_url",
        help="相簿頁面 URL（如 https://18comic.vip/album/1223474/）",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="./output",
        help="輸出目錄（預設：./output）",
    )
    parser.add_argument(
        "--headless/--no-headless",
        dest="headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否使用無頭瀏覽器模式",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="每張圖片下載間隔秒數（預設：0.3）",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="從第幾話開始下載（預設：1）",
    )
    parser.add_argument(
        "--end-at",
        type=int,
        default=None,
        help="下載到第幾話結束（預設：全部）",
    )
    
    args = parser.parse_args()
    
    # 建立輸出目錄
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 正在解析相簿: {args.album_url}")
    
    try:
        # 提取章節列表
        album_title, chapters = extract_album_chapters(args.album_url, headless=args.headless)
        
        print(f"\n📚 相簿標題: {album_title}")
        print(f"📖 共 {len(chapters)} 個章節（已過濾休刊公告）")
        
        if not chapters:
            print("❌ 未找到任何章節")
            sys.exit(1)
        
        # 建立相簿目錄
        # 清理標題中的特殊字元（防止路徑遍歷攻擊）
        safe_title = sanitize_filename(album_title)
        album_dir = output_dir / safe_title
        album_dir.mkdir(exist_ok=True)
        
        images_dir = album_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        pdf_dir = album_dir / "pdf"
        pdf_dir.mkdir(exist_ok=True)
        
        # 篩選要下載的章節
        chapters_to_download = [
            ch for ch in chapters
            if ch.episode_num >= args.start_from
            and (args.end_at is None or ch.episode_num <= args.end_at)
        ]
        
        print(f"\n⬇️  將下載 {len(chapters_to_download)} 個章節")
        print(f"   圖片目錄: {images_dir}")
        print(f"   PDF 目錄: {pdf_dir}")
        
        # 依序下載每個章節
        for chapter in chapters_to_download:
            try:
                # 下載圖片
                chapter_image_dir = download_chapter_images(
                    chapter,
                    images_dir,
                    headless=args.headless,
                    delay=args.delay,
                )
                
                # 生成 PDF
                pdf_filename = f"ep{chapter.episode_num:03d}.pdf"
                pdf_path = pdf_dir / pdf_filename
                
                if not pdf_path.exists():
                    print(f"   📄 生成 PDF: {pdf_filename}")
                    images_to_pdf(chapter_image_dir, pdf_path)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  使用者中斷")
                sys.exit(1)
            except Exception as e:
                print(f"   ❌ 錯誤: {e}")
                continue
            
            # 章節間延遲
            time.sleep(1)
        
        print(f"\n🎉 完成！")
        print(f"   圖片: {images_dir}")
        print(f"   PDF:  {pdf_dir}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
