import requests
from bson import ObjectId
import requests
from bson import ObjectId
from flask import Flask, jsonify
from selenium import webdriver
# from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from threading import Thread
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from flask import request
from bs4 import BeautifulSoup
from pyvirtualdisplay import Display
from selenium.webdriver.common.proxy import Proxy, ProxyType
import random
import concurrent.futures
import sys

from src.database import collection, collection_youtube, collection_order, collection_ips
sys.path.append("C:/Python Selenium/youtube_automation_project")

app = Flask(__name__)

chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")


# Api Function
def generate_random_number(half_length_of_video_from_database, full_length_of_video_from_database):
    return random.randint(half_length_of_video_from_database, full_length_of_video_from_database)


def get_active_emails(emails_data):
    return [email.get('email') for email in emails_data if email.get('status') == 'active']


def get_filtered_target_views(order_data):
    return [order_info.get("target_views") for order_info in order_data if order_info.get("order_status") == "pending"]


def get_video_links_for_pending_orders(pending_orders, collection_youtube):
    video_links_array = []
    for order in pending_orders:
        video_id = str(order.get("video"))  # Convert ObjectId to string
        video_entry = collection_youtube.find_one({"_id": ObjectId(video_id)})
        if video_entry:
            video_link = video_entry.get("video_link")
            print(f"Video Link for Order ID {str(order['_id'])}: {video_link}")
            video_links_array.append(video_link)
        else:
            print(f"No corresponding video entry found for Order ID {str(order['_id'])}")
    return video_links_array


def is_connected_to_network():
    try:
        # Try to make a request to a known website (e.g., Google)
        response = requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False


def convert_duration_to_seconds_and_round(duration_str):
    # Split the duration string into hours, minutes, and seconds
    parts = duration_str.split(':')

    if len(parts) == 3:
        # If there are three parts, consider them as hours, minutes, and seconds
        hours, minutes, seconds = map(int, parts)
    elif len(parts) == 2:
        # If there are two parts, consider them as minutes and seconds
        hours = 0
        minutes, seconds = map(int, parts)
    else:
        # If there is only one part, consider it as seconds
        hours = 0
        minutes = 0
        seconds = int(parts[0])

    # Calculate total seconds
    total_seconds = hours * 3600 + minutes * 60 + seconds
    # Calculate half of the total seconds and round
    half_seconds_rounded = round(total_seconds / 2)

    return duration_str, hours, minutes, seconds, total_seconds, half_seconds_rounded








