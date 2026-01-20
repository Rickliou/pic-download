"""
圖片還原演算法單元測試
"""
import hashlib
import pytest
from descrambler import get_num, SEGMENT_MAP


class TestGetNum:
    """測試 get_num 函數"""
    
    def test_aid_below_threshold_returns_zero(self):
        """aid 低於閾值時應返回 0（不需解混淆）"""
        assert get_num(100000, "00001") == 0
        assert get_num(220979, "00001") == 0
    
    def test_aid_at_threshold_returns_nonzero(self):
        """aid 達到閾值時應返回 > 0"""
        result = get_num(220980, "00001")
        assert result in SEGMENT_MAP
    
    def test_known_example_aid_1223474(self):
        """測試已知例子：aid=1223474, photo_id=00001 應返回 6"""
        # 根據瀏覽器分析：
        # MD5("122347400001") 的最後一個字元是 '2'
        # ord('2') = 50, 50 % 8 = 2
        # SEGMENT_MAP[2] = 6
        result = get_num(1223474, "00001")
        assert result == 6
    
    def test_consistency(self):
        """相同輸入應產生相同輸出"""
        result1 = get_num(1223474, "00005")
        result2 = get_num(1223474, "00005")
        assert result1 == result2
    
    def test_different_photos_may_differ(self):
        """不同 photo_id 可能產生不同分段數"""
        results = set()
        for i in range(1, 20):
            photo_id = f"{i:05d}"
            results.add(get_num(1223474, photo_id))
        # 應該有多種不同的分段數
        assert len(results) >= 2
    
    def test_md5_calculation_correctness(self):
        """驗證 MD5 計算邏輯"""
        # 手動計算 MD5("122347400001")
        combined = "122347400001"
        expected_hash = hashlib.md5(combined.encode()).hexdigest()
        last_char = expected_hash[-1]
        
        # 驗證預期值
        assert last_char == '2'  # 根據瀏覽器測試結果
    
    def test_range_268850_to_421925(self):
        """測試 268850 <= aid <= 421925 範圍（使用 % 10）"""
        # 這個範圍使用 charCode % 10
        result = get_num(300000, "00001")
        assert result in SEGMENT_MAP
    
    def test_range_above_421926(self):
        """測試 aid >= 421926 範圍（使用 % 8）"""
        # 這個範圍使用 charCode % 8，所以結果只能是前 8 個
        for _ in range(10):
            result = get_num(500000, f"{_:05d}")
            # 因為 index = charCode % 8，index 最大為 7
            # SEGMENT_MAP[0:8] = [2, 4, 6, 8, 10, 12, 14, 16]
            assert result in [2, 4, 6, 8, 10, 12, 14, 16]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
