import os
import sys

# src/app_news_summarizer.py 로직 동기화
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app_news_summarizer import *
