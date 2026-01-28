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
# 基本使用（預設儲存到 ./output）
python main.py https://18comic.vip/photo/1223474

# 指定輸出目錄到桌面
python main.py https://18comic.vip/photo/1223474 -o ~/Desktop/my_comics

# 指定輸出目錄到 Documents
python main.py https://18comic.vip/photo/1223474 --output-dir ~/Documents/comics

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

### 基本用法

```bash
# 下載整個相簿（預設儲存到 ./output）
python batch_download.py "https://18comic.vip/album/1223474/"

# 指定輸出目錄
python batch_download.py "https://18comic.vip/album/1223474/" -o /Volumes/TR_004/

# 只下載第 10~20 話
python batch_download.py "https://18comic.vip/album/1223474/" --start-from 10 --end-at 20

# 指定輸出目錄並下載特定範圍
python batch_download.py "https://18comic.vip/album/1223474/" -o ~/Documents/comics --start-from 5 --end-at 15
```

### 完整參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `album_url` | 相簿頁面網址 | (必填) |
| `--output-dir`, `-o` | 輸出目錄 | `./output` |
| `--headless` | 無頭模式 | 開啟 |
| `--delay` | 下載間隔秒數 | `0.3` |
| `--start-from` | 從第幾話開始下載 | `1` |
| `--end-at` | 下載到第幾話結束 | 全部 |

### 輸出結構

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

## 遠端運行與後台任務

### 使用 tmux 保持程式運行

當需要透過 SSH/VPN 遠端執行長時間任務時，使用 tmux 可以讓程式在斷線後繼續執行。

#### 安裝 tmux

```bash
# macOS
brew install tmux

# Linux (遠端伺服器)
sudo apt-get install tmux
```

#### 基本使用流程

1. **創建 tmux session**
   ```bash
   tmux new -s download
   ```

2. **在 tmux 中執行下載程式**
   ```bash
   python batch_download.py "https://18comic.vip/album/1223474/"
   ```

3. **分離 session（讓程式在背景執行）**
   - 按 `Ctrl + B`
   - 放開兩個鍵
   - 按 `D`
   
   成功時會顯示：`[detached (from session download)]`

4. **現在可以安全地關閉視窗或斷開連線**
   - 程式會繼續在遠端執行
   - 可以關閉 terminal 視窗
   - 可以斷開 VPN 連線

5. **重新連線查看進度**
   ```bash
   # 列出所有 sessions
   tmux ls
   
   # 重新連接到指定 session
   tmux attach -t download
   ```

#### 常用快捷鍵

| 快捷鍵 | 功能 |
|--------|------|
| `Ctrl + B` → `D` | 分離 session |
| `Ctrl + B` → `C` | 創建新視窗 |
| `Ctrl + B` → `W` | 列出所有視窗 |
| `Ctrl + B` → `0-9` | 切換到指定視窗 |
| `Ctrl + B` → `%` | 垂直分割視窗 |
| `Ctrl + B` → `"` | 水平分割視窗 |

注意：macOS 上也是使用 `Ctrl` 鍵，不是 `Command` 鍵。

#### 其他後台執行方式

如果不想使用 tmux，也可以使用 `nohup`：

```bash
# 基本用法
nohup python batch_download.py "URL" &

# 將輸出記錄到檔案
nohup python batch_download.py "URL" > download.log 2>&1 &

# 查看背景程序
ps aux | grep python
```

## 還原演算法

網站將圖片水平切割成 N 段並垂直翻轉順序。還原公式：

```
N = SEGMENT_MAP[MD5(aid + photo_id)[-1] % 8]
H_slice = H // N
Remainder = H % N
```

從原圖底部往上取出 N 段，依序放到新圖頂部往下。
