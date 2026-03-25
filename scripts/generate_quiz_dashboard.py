#!/usr/bin/env python3
"""
電験3種 テスト記録ダッシュボード生成スクリプト
data/records.json → quiz.html
"""
import json, os
from datetime import date, timedelta
from collections import defaultdict, Counter

RECORDS_PATH = "data/records.json"
OUTPUT_PATH  = "quiz.html"
SUBJECT_ORDER = ["理論", "電力", "機械", "法規"]
REVIEW_DAYS   = {"SR1": 1, "SR2": 3, "SR3": 7, "SR4": 14, "SR5": 30, "done": 9999}