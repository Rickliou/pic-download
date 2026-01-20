"""
18comic 圖片還原模組

此模組實作圖片解混淆（descramble）演算法，將被切割打亂的圖片還原為正確順序。

演算法說明：
1. 網站將原圖水平切割成 N 段，並垂直翻轉順序（底部變頂部）
2. 還原時需將圖片從底部往上取出各段，依序放到新圖的頂部往下
"""
import hashlib
from io import BytesIO
from PIL import Image


# 分段數映射表（index -> 實際分段數）
SEGMENT_MAP = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]

# 混淆演算法閾值
SCRAMBLE_THRESHOLD = 220980
RANGE_268850_421925 = (268850, 421925)
RANGE_421926_PLUS = 421926


def get_num(aid: int, photo_id: str) -> int:
    """
    計算圖片的分段數量。
    
    演算法步驟：
    1. 將 aid（字串）與 photo_id 串接
    2. 計算 MD5 雜湊值
    3. 取最後一個字元的 ASCII 碼
    4. 根據 aid 範圍決定取餘數的基數
    5. 用餘數作為 index 從映射表取得分段數
    
    Args:
        aid: 相簿 ID（整數）
        photo_id: 圖片編號（如 "00001"）
    
    Returns:
        int: 圖片被切割的分段數（2, 4, 6, 8, 10, 12, 14, 16, 18, 或 20）
    """
    # 若 aid 小於閾值，不需要解混淆
    if aid < SCRAMBLE_THRESHOLD:
        return 0
    
    # 計算 MD5(aid + photo_id)
    combined = str(aid) + photo_id
    md5_hash = hashlib.md5(combined.encode()).hexdigest()
    
    # 取最後一個字元的 ASCII 碼
    last_char = md5_hash[-1]
    char_code = ord(last_char)
    
    # 根據 aid 範圍決定取餘數
    if RANGE_268850_421925[0] <= aid <= RANGE_268850_421925[1]:
        index = char_code % 10
    elif aid >= RANGE_421926_PLUS:
        index = char_code % 8
    else:
        # aid 在 220980 ~ 268849 之間，使用預設值
        index = char_code % 10
    
    return SEGMENT_MAP[index]


def restore_image(scrambled_data: bytes, aid: int, photo_id: str) -> Image.Image:
    """
    還原被混淆的圖片。
    
    還原公式：
    - H: 原圖高度
    - W: 原圖寬度  
    - N: 分段數（由 get_num 計算）
    - H_slice = floor(H / N)：每段高度
    - Remainder = H % N：餘數（加到第一段）
    
    還原邏輯（模擬網頁 Canvas drawImage）：
    ```
    for g in range(N):
        h = H_slice                      # 當前段高度
        u = H_slice * g                  # 目標 Y 座標
        p = H - H_slice * (g + 1) - f    # 來源 Y 座標（從底部往上取）
        
        if g == 0:
            h += Remainder               # 第一段加上餘數
        else:
            u += Remainder               # 後續段的目標 Y 需加上餘數偏移
        
        draw(src=(0, p, W, h), dst=(0, u, W, h))
    ```
    
    Args:
        scrambled_data: 混淆圖片的二進位資料
        aid: 相簿 ID
        photo_id: 圖片編號（如 "00001"）
    
    Returns:
        PIL.Image.Image: 還原後的圖片物件
    """
    # 載入圖片
    scrambled_img = Image.open(BytesIO(scrambled_data))
    width, height = scrambled_img.size
    
    # 計算分段數
    num_segments = get_num(aid, photo_id)
    
    # 若不需要解混淆，直接返回
    if num_segments == 0:
        return scrambled_img
    
    # 建立新的空白圖片
    restored_img = Image.new(scrambled_img.mode, (width, height))
    
    # 計算每段高度與餘數
    slice_height = height // num_segments  # H_slice = floor(H / N)
    remainder = height % num_segments      # Remainder = H % N
    
    # 依照網頁 JS 邏輯還原
    # 原始 JS：
    # for (var g = 0; g < c; g++) {
    #     var h = Math.floor(height / c),
    #         u = h * g,
    #         p = height - h * (g + 1) - f;
    #     if (g == 0) h += f; else u += f;
    #     context.drawImage(img, 0, p, width, h, 0, u, width, h);
    # }
    for g in range(num_segments):
        h = slice_height                           # 當前段高度
        u = slice_height * g                       # 目標 Y 座標（新圖）
        p = height - slice_height * (g + 1) - remainder  # 來源 Y 座標（原圖，從底部往上）
        
        if g == 0:
            h += remainder  # 第一段加上餘數高度
        else:
            u += remainder  # 後續段的目標 Y 座標需加上餘數偏移
        
        # 從原圖裁切區塊
        # crop box: (left, upper, right, lower)
        box = (0, p, width, p + h)
        segment = scrambled_img.crop(box)
        
        # 貼到新圖的目標位置
        restored_img.paste(segment, (0, u))
    
    return restored_img


def restore_image_from_file(input_path: str, output_path: str, aid: int, photo_id: str) -> None:
    """
    從檔案讀取混淆圖片並還原後儲存。
    
    Args:
        input_path: 輸入圖片路徑
        output_path: 輸出圖片路徑
        aid: 相簿 ID
        photo_id: 圖片編號
    """
    with open(input_path, "rb") as f:
        scrambled_data = f.read()
    
    restored = restore_image(scrambled_data, aid, photo_id)
    restored.save(output_path)
