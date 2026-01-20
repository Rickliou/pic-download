#!/usr/bin/env python3
"""
18comic 圖片抓取與還原工具

用法：
    python main.py <URL> [--output-dir OUTPUT_DIR] [--headless/--no-headless]

範例：
    python main.py https://18comic.vip/photo/1223474 --output-dir ./output
"""
import argparse
import sys
import time
import random
from pathlib import Path

from descrambler import restore_image
from scraper import scrape_album, download_image


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="18comic 圖片抓取與還原工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "url",
        help="相簿頁面 URL（如 https://18comic.vip/photo/1223474）",
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
        help="是否使用無頭瀏覽器模式（預設：是）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="每張圖片下載間隔秒數（預設：0.5）",
    )
    
    args = parser.parse_args()
    
    # 建立輸出目錄
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔍 正在解析頁面: {args.url}")
    
    try:
        # 爬取相簿資訊
        album = scrape_album(args.url, headless=args.headless)
        print(f"📚 相簿標題: {album.title}")
        print(f"🆔 相簿 ID: {album.aid}")
        print(f"🖼️  共找到 {len(album.images)} 張圖片")
        
        if not album.images:
            print("❌ 未找到任何圖片")
            sys.exit(1)
        
        # 建立以 aid 命名的子目錄
        album_dir = output_dir / str(album.aid)
        album_dir.mkdir(exist_ok=True)
        
        # 下載並還原每張圖片
        for img_info in album.images:
            # 輸出檔名：按順序編號 + 原始 photo_id
            output_filename = f"{img_info.index:04d}_{img_info.photo_id}.webp"
            output_path = album_dir / output_filename
            
            # 檢查是否已存在
            if output_path.exists():
                print(f"  ⏭️  [{img_info.index}/{len(album.images)}] 已存在，跳過")
                continue
            
            print(f"  📥 [{img_info.index}/{len(album.images)}] 下載中: {img_info.photo_id}...", end=" ")
            
            try:
                # 下載圖片
                scrambled_data = download_image(img_info.url, referer=args.url)
                
                # 還原圖片
                restored_img = restore_image(scrambled_data, album.aid, img_info.photo_id)
                
                # 儲存
                restored_img.save(output_path)
                print(f"✅ 完成")
                
            except Exception as e:
                print(f"❌ 失敗: {e}")
                continue
            
            # 隨機延遲，避免請求過於頻繁
            delay = args.delay + random.uniform(0, 0.3)
            time.sleep(delay)
        
        print(f"\n🎉 完成！圖片已儲存至: {album_dir.absolute()}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
