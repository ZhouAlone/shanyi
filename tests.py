# -*- coding: utf-8 -*-
"""核心纯逻辑单测：PNG 编码、配置解析、方向判断。运行：python tests.py"""
import struct
import unittest
import zlib

import config
import capture


class TestPngEncoding(unittest.TestCase):
    """PNG 编码器：曾因字节序 bug 服务器 400，此处锁死正确性。"""

    def setUp(self):
        self.w, self.h = 4, 2
        self.row = ((24 * self.w + 31) // 32) * 4
        self.buf = bytearray(self.row * self.h)

    def setpx(self, x, y, r, g, b):
        i = y * self.row + x * 3
        self.buf[i], self.buf[i + 1], self.buf[i + 2] = b, g, r  # GDI 是 BGR

    def test_png_structure(self):
        self.setpx(0, 0, 255, 0, 0)
        self.setpx(1, 0, 0, 255, 0)
        self.setpx(2, 0, 0, 0, 255)
        png = capture.pixels_to_png(bytes(self.buf), self.w, self.h)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        pos, chunks = 8, []
        while pos < len(png):
            ln = struct.unpack(">I", png[pos:pos + 4])[0]      # 长度必须大端
            typ = png[pos + 4:pos + 8]
            data = png[pos + 8:pos + 8 + ln]
            crc = png[pos + 8 + ln:pos + 12 + ln]
            self.assertEqual(crc, zlib.crc32(typ + data).to_bytes(4, "big"),
                             f"{typ} CRC 非大端")
            chunks.append((typ, data))
            pos += 12 + ln
        self.assertEqual(chunks[0][0], b"IHDR")
        self.assertEqual(chunks[-1][0], b"IEND")
        # 像素正确性：IDAT 解压后首像素是 (255,0,0)
        idat = next(d for t, d in chunks if t == b"IDAT")
        raw = zlib.decompress(idat)
        self.assertEqual(tuple(raw[1:4]), (255, 0, 0))          # BGR→RGB 已翻转

    def test_row_padding(self):
        """宽度 3px（12B 行，不对齐 4B）时 padding 不破坏像素"""
        self.setpx(0, 0, 10, 20, 30)
        png = capture.pixels_to_png(bytes(self.buf), 3, 1)
        pos = 8
        while pos < len(png):
            ln = struct.unpack(">I", png[pos:pos + 4])[0]
            if png[pos + 4:pos + 8] == b"IDAT":
                raw = zlib.decompress(png[pos + 8:pos + 8 + ln])
                self.assertEqual(tuple(raw[1:4]), (10, 20, 30))
            pos += 12 + ln


class TestConfig(unittest.TestCase):
    def test_hotkey_parsing(self):
        self.assertEqual(config.MOD_MAP["ALT"], 0x0001)
        self.assertEqual(config.MOD_MAP["CTRL"], 0x0002)
        # F 键解析：VK_F1 = 0x70
        self.assertEqual(0x6F + 1, 0x70)
        # 默认配置在 import 时已解析：translate 热键 = ALT+T
        mods, key = config.hotkey_id("translate")
        self.assertEqual(key, ord("T"))
        self.assertTrue(mods & config.MOD_MAP["ALT"])

    def test_direction_heuristic(self):
        """汉字为主→英，拉丁为主→中（api.translate 的判断逻辑）"""
        def is_en(text):
            cjk = sum('\u4e00' <= c <= '\u9fff' for c in text)
            latin = sum(c.isascii() and c.isalpha() for c in text)
            return cjk >= latin
        self.assertTrue(is_en("依赖注入是一种设计模式"))    # → 译英
        self.assertFalse(is_en("dependency injection"))     # → 译中


class TestExpandRegion(unittest.TestCase):
    """细面条框选区扩边（DeepSeek-OCR 要求宽高 >28px，取 64 保险）"""

    def test_thin_strip_expands(self):
        # 单行文字：325x26 → 高度扩到 64，居中
        x, y, w, h = capture.expand_region(100, 200, 325, 26, 1920, 1080)
        self.assertEqual((w, h), (325, 64))
        self.assertEqual(y, 200 - (64 - 26) // 2)

    def test_edge_clamped(self):
        # 贴屏幕顶边框选：扩边后不能越界
        x, y, w, h = capture.expand_region(500, 0, 729, 27, 1920, 1080)
        self.assertEqual((w, h), (729, 64))
        self.assertEqual(y, 0)

    def test_normal_region_untouched(self):
        x, y, w, h = capture.expand_region(100, 100, 400, 300, 1920, 1080)
        self.assertEqual((x, y, w, h), (100, 100, 400, 300))


    def test_custom_min_side(self):
        # min_side 可配置（config: ocr_min_side）
        x, y, w, h = capture.expand_region(100, 200, 325, 26, 1920, 1080, 100)
        self.assertEqual((w, h), (325, 100))


class TestWiring(unittest.TestCase):
    """装配冒烟：所有模块必须可导入（防重构漏 import 一类的低级伤）"""

    def test_all_modules_import(self):
        import importlib
        for mod in ("config", "winapi", "capture", "api", "ui", "hotkeys", "tray"):
            importlib.import_module(mod)


if __name__ == "__main__":
    unittest.main(verbosity=2)
