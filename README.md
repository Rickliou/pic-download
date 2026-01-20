# 18comic 圖片還原工具

從 18comic 頁面自動抓取並還原被混淆切割的圖片。

## 安裝

```bash
# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 安裝瀏覽器
python -m playwright install chromium
```

## 使用方式

### 基本用法

```bash
python main.py <相簿URL>
```

### 完整參數

```bash
python main.py <URL> [--output-dir DIR] [--headless/--no-headless] [--delay SECONDS]
```

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `URL` | 相簿頁面網址 | (必填) |
| `--output-dir`, `-o` | 輸出目錄 | `./output` |
| `--headless` | 無頭模式（隱藏瀏覽器） | 開啟 |
| `--no-headless` | 顯示瀏覽器視窗 | - |
| `--delay` | 下載間隔秒數 | `0.5` |

### 範例

```bash
# 基本使用
python main.py https://18comic.vip/photo/1223474

# 指定輸出目錄
python main.py https://18comic.vip/photo/1223474 -o ~/Downloads/comics

# 顯示瀏覽器視窗（除錯用）
python main.py https://18comic.vip/photo/1223474 --no-headless
```

## 輸出結構

```
output/
└── {相簿ID}/
    ├── 0001_00001.webp
    ├── 0002_00002.webp
    └── ...
```

## 模組說明

| 檔案 | 功能 |
|------|------|
| `descrambler.py` | 圖片還原核心演算法 |
| `scraper.py` | Playwright 頁面爬取 |
| `main.py` | 單一章節下載 |
| `batch_download.py` | 相簿批量下載 |
| `to_pdf.py` | 圖片轉 PDF 工具 |

## 批量下載整個相簿

```bash
python batch_download.py "https://18comic.vip/album/1223474/"

# 只下載第 10~20 話
python batch_download.py "https://18comic.vip/album/1223474/" --start-from 10 --end-at 20
```

輸出結構：
```
output/{相簿名稱}/
├── images/ep001_{id}/    # 原始圖片
└── pdf/ep001.pdf         # PDF 檔案
```

## 轉換為 PDF

下載完成後，可將圖片合併成 PDF 以便連續閱讀：

```bash
# 基本用法
python to_pdf.py ./output/{相簿ID}

# 指定輸出路徑
python to_pdf.py ./output/1223474 -o ~/Documents/comic.pdf
```

## 還原演算法

網站將圖片水平切割成 N 段並垂直翻轉順序。還原公式：

```
N = SEGMENT_MAP[MD5(aid + photo_id)[-1] % 8]
H_slice = H // N
Remainder = H % N
```

從原圖底部往上取出 N 段，依序放到新圖頂部往下。
