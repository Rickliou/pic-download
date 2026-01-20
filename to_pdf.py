#!/usr/bin/env python3
"""
圖片轉 PDF 工具

將指定目錄中的圖片合併成一個可連續觀看的 PDF 檔案。
"""
import argparse
from pathlib import Path
from PIL import Image


def images_to_pdf(image_dir: Path, output_path: Path) -> None:
    """
    將目錄中的圖片合併成 PDF。
    
    Args:
        image_dir: 圖片目錄
        output_path: 輸出 PDF 路徑
    """
    # 支援的圖片格式
    extensions = {".webp", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}
    
    # 取得所有圖片並排序
    image_files = sorted(
        [f for f in image_dir.iterdir() if f.suffix.lower() in extensions]
    )
    
    if not image_files:
        raise ValueError(f"目錄 {image_dir} 中未找到圖片")
    
    print(f"📚 找到 {len(image_files)} 張圖片")
    
    # 載入所有圖片並轉換為 RGB（PDF 需要）
    images = []
    for img_path in image_files:
        img = Image.open(img_path)
        # 轉換為 RGB（處理 RGBA 或其他模式）
        if img.mode in ("RGBA", "P", "LA"):
            # 建立白色背景
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        images.append(img)
        print(f"  ✓ 載入: {img_path.name}")
    
    # 第一張圖片作為基底，其餘附加
    first_image = images[0]
    other_images = images[1:]
    
    # 儲存為 PDF
    first_image.save(
        output_path,
        "PDF",
        resolution=100.0,
        save_all=True,
        append_images=other_images,
    )
    
    print(f"\n🎉 PDF 已儲存至: {output_path}")


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="將圖片目錄轉換為 PDF",
    )
    parser.add_argument(
        "image_dir",
        help="圖片目錄路徑",
    )
    parser.add_argument(
        "--output", "-o",
        help="輸出 PDF 路徑（預設：{目錄名}.pdf）",
    )
    
    args = parser.parse_args()
    
    image_dir = Path(args.image_dir)
    if not image_dir.is_dir():
        print(f"❌ 目錄不存在: {image_dir}")
        return 1
    
    # 決定輸出路徑
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = image_dir.parent / f"{image_dir.name}.pdf"
    
    images_to_pdf(image_dir, output_path)
    return 0


if __name__ == "__main__":
    exit(main())
