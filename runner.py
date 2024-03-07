import logging
import os
import shutil
from jinja2 import FileSystemLoader, Environment
import concurrent.futures
import random
from threading import Thread
from time import sleep
import requests
import atexit
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, send_file
from flask import request
from pymongo import MongoClient
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS
from src.utils import (is_connected_to_network,
                       get_active_emails, get_filtered_target_views,
                       get_video_links_for_pending_orders, generate_random_number,
                       convert_duration_to_seconds_and_round)
from src.database import collection, collection_youtube, collection_order, collection_ips

app = Flask(__name__)
CORS(app)

drivers = []
current_position = 0


# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
# chrome_options.add_argument("--headless")



def perform_like_action(driver, action):
    try:
        for _ in range(1):
            print(action)
            if action == 'like':
                like_xpath = ('//*[@id="top-level-buttons-computed"]/segmented-like-dislike-button-view-model/yt-smartimation/div/div/like-button-view-model/toggle-button-view-model')
                like_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, like_xpath))
                )
                if like_button:
                    print("like_button")
                    sleep(5)
                    like_button.click()
                    print(f'Like button found and clicked')
                sleep(5)
                subscribe_button_selector = '#subscribe-button-shape > button'
                subscribe_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, subscribe_button_selector))
                )
                if subscribe_button:
                    print(f'subscribe button found and clicked')
                    subscribe_button.click()
                    subscribe_button_selector_notification = ('#notification-preference-button > '
                                                              'ytd-subscription-notification-toggle-button-renderer'
                                                              '-next > yt-button-shape > button')
                    subscribe_button_notification = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, subscribe_button_selector_notification))
                    )
                    if subscribe_button_notification:
                        sleep(2)
                        print(f'subscribe notification button found and clicked')
                        subscribe_button_notification.click()
                    all_notification_selector = ('#items > ytd-menu-service-item-renderer.style-scope.ytd-menu-popup'
                                                 '-renderer.iron-selected')
                    all_notification_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, all_notification_selector))
                    )
                    if all_notification_button:
                        sleep(2)
                        print(f'All notification allow button found and clicked')
                        all_notification_button.click()
                        sleep(3)


    except TimeoutException:
        print(f'Timeout: {action.capitalize()} button not found')
    except NoSuchElementException:
        print(f'Element not found: {action.capitalize()} button not present on the page')


def open_youtube_video(driver, youtube_video_url):
    global current_action, process_subscribe, target_subscribe, object_id
    driver.execute_script(f"window.open('{youtube_video_url}', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    try:
        perform_like_action(driver, "like")
    except TimeoutException:
        print(f'Timeout: {current_action.capitalize()} button not found')
    except NoSuchElementException:
        print(f'Element not found: {current_action.capitalize()} button not present on the page')
    driver.switch_to.window(driver.window_handles[0])


def go_to_youtube_and_view_video_after_login(video_urls_array, driver):
    with app.app_context():
        if is_connected_to_network():
            try:
                for youtube_video_url in video_urls_array:
                    open_youtube_video(driver, youtube_video_url)
                return jsonify({
                    "status": "success",
                    "message": "All videos liked successfully in separate tabs."
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"An error occurred: {str(e)}"
                })
        else:
            return jsonify({
                "status": "error",
                "message": "Not connected to the network."
            })


def login_to_gmail_and_store_driver(email, password, video_urls_array):
    with app.app_context():
        sleep(2)
        driver = webdriver.Chrome(options=chrome_options)
        youtube_url = "https://www.youtube.com/"
        driver.get(youtube_url)
        
        url = "https://accounts.google.com/v3/signin/identifier?authuser=0&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fdata&ec=GAlAFw&hl=en&service=mail&flowName=GlifWebSignIn&flowEntry=AddSession&dsh=S-1056250542%3A1700483692061719&theme=glif"
        driver.get(url)
        driver.maximize_window()
        try:
            username_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            username_input.send_keys(email)
            driver.find_element(By.ID, 'identifierNext').click()
            try:
                invalid_email_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(text(), 'Could’t find your Google Account')]"))
                )
                if invalid_email_element:
                    driver.quit()
                    print("Invalid email or email not found.")
                    return {"error": "Invalid email or email not found."}
            except:
                pass
            password_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "Passwd"))
            )
            password_input.send_keys(password)
            driver.find_element(By.ID, "passwordNext").click()

            # Check if the password entered is incorrect
            try:
                incorrect_password_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "//span[contains(text(), 'Wrong password. Try again or click "
                                                    "Forgot password to reset it.')]"))
                )
                if incorrect_password_element:
                    driver.quit()
                    print("incorrect Password")
                    return {"error": "Incorrect password."}
            except:
                pass

            WebDriverWait(driver, 20).until(
                EC.url_contains("mail.google.com")
            )
            # Check if phone number verification is required
            try:
                verify_you_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="headingText"]/span'))
                )
                if verify_you_element and verify_you_element.text == "Verify it’s you":
                    print("verify gmail")
                    result_set = {"Verify it’s you."}
                    driver.quit()
                    return {"result": list(result_set)}
            except:
                pass

            print(f"Logged in successfully with {email} and Gmail is connected.")
            sleep(10)
            go_to_youtube_and_view_video_after_login(video_urls_array, driver)
            driver.quit()
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error: {e}")
            try:
                collection.update_one(
                    {"email": email},
                    {"$set": {"status": "Inactive"}}
                )
            except Exception as e:
                print(f"Error occurred during database update: {str(e)}")
            driver.quit()
        finally:
            drivers.append(driver)                  


def login_to_gmail_with_limit_api(limit):
    global current_position
    if is_connected_to_network():
        # video_urls_array = get_video_links_for_pending_orders(pending_orders, collection_youtube)
        video_urls_array =["https://www.youtube.com/watch?v=JwbWqVznxTg"]
        emails_data_here = collection.find().skip(current_position).limit(limit)
        current_position += limit
        threads = []
        for email_data in emails_data_here:
            email = email_data["email"]
            password = email_data["password"]
            print(email, password)
            thread = Thread(target=login_to_gmail_and_store_driver, args=(email, password, video_urls_array))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
    else:
        return jsonify({"status": "error", "message": "Not connected to the network."})


# @app.route('/go_to_youtube_and_view_video', methods=['POST'])
@app.route('/go_to_youtube_and_view_video', methods=['POST'])
def go_to_youtube_and_view_video():
    emails_data = list(collection.find())
    order_data = list(collection_order.find())
    limit = int(1)
    active_emails_only = get_active_emails(emails_data)
    emails_only_length = len(active_emails_only)
    print(f"Number of documents in the database Email: {emails_only_length}")

    filtered_target_views = get_filtered_target_views(order_data)
    print(filtered_target_views, "filtered_target_views")

    if filtered_target_views:
        filtered_target_views = list(map(int, filtered_target_views))
        maximum_number = max(filtered_target_views)
        print(maximum_number, "maximum Number")

        if is_connected_to_network():
            views_count = 0
            while views_count < int(maximum_number):
                if views_count < emails_only_length:
                    login_to_gmail_with_limit_api(limit)
                    views_count += limit
                    print(views_count)
                else:
                    try:
                        print("Reached total_views_limit. Opening four new browser instances without logging in.")
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            tasks = [
                                executor.submit(login_to_gmail_with_limit_api_for_without_login, limit)
                                for _ in range(limit)
                            ]
                            concurrent.futures.wait(tasks)
                        views_count += limit
                        print(views_count)
                    except Exception as e:
                        print(f"An error occurred: {str(e)}")
            return jsonify(
                {"status": "success", "message": "All browsers are navigating to the YouTube channel."})
        else:
            return jsonify({"status": "error", "message": "Not connected to the network."})
    else:
        maximum_number = 0
        print("filtered_target_views is empty!")


go_to_youtube_and_view_video()