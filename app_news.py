import os
import sys

# src 디렉터리를 sys.path에 추가하여 app_news_summarizer 실행
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from app_news_summarizer import *
