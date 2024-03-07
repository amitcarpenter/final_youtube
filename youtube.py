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
chrome_options.add_argument("--headless")


# @app.route('/check_video_duration', methods=['POST'])
# def check_video_duration_api():
#     if not request.is_json:
#         return jsonify({"status": "error", "message": "Invalid request format. JSON expected."})
#     data = request.get_json()
#     video_url = data.get('video_url')
#     if not video_url:
#         return jsonify({"status": "error", "message": "Missing 'video_url' parameter."})
#     if is_connected_to_network():
#         # display = Display(visible=0, size=(800, 600))
#         # display.start()
#         chrome_options = webdriver.ChromeOptions()
#         chrome_options.add_argument('--no-sandbox')
#         chrome_options.add_argument('--headless')
#         driver = webdriver.Chrome(options=chrome_options)
#         driver.get(video_url)
#         sleep(1)
#         page_source = driver.page_source
#         driver.quit()
#         display.stop()
#         soup = BeautifulSoup(page_source, 'html.parser')
#         subscriber_count_element = soup.find('yt-formatted-string', id='owner-sub-count')
#         duration_element = soup.find('span', class_='ytp-time-duration')
#         channel_name_element = soup.find('yt-formatted-string', class_='style-scope ytd-channel-name')

#         if duration_element and subscriber_count_element and channel_name_element:
#             video_duration_str, hours, minutes, seconds, total_seconds, half_seconds_rounded = convert_duration_to_seconds_and_round(
#                 duration_element.text)
#             print(video_duration_str, hours, minutes, seconds, total_seconds, half_seconds_rounded)
#             subscriber_count_text = subscriber_count_element.text
#             trimmed_text = subscriber_count_text.split()[0]
#             channel_name = channel_name_element.text.strip()
#             return jsonify({
#                 "status": "success",
#                 "video_duration": video_duration_str,
#                 "total_seconds": total_seconds,
#                 "half_seconds_rounded": half_seconds_rounded,
#                 "subscriber_count": trimmed_text,
#                 "channel_name": channel_name,
#             })

#         else:
#             return jsonify({"status": "error", "message": "Unable to find video duration element."})
#     else:
#         return jsonify({"status": "error", "message": "Not connected to the network."})


def process_video_data(video_info):
    youtube_video_url = video_info.get("video_link")
    youtube_video_views_target = video_info.get("target_views")

    return {
        "youtube_video_url": youtube_video_url,
        "youtube_video_views_target": youtube_video_views_target,
    }


current_action = 'like'


# With Login
def perform_like_action(driver, action):
    try:
        for _ in range(1):
            print(action)
            if action == 'like':
                like_button_selector = ('#top-level-buttons-computed > segmented-like-dislike-button-view-model > '
                                        'yt-smartimation > div > div > like-button-view-model > '
                                        'toggle-button-view-model > button')
                like_xpath = ('//*[@id="top-level-buttons-computed"]/segmented-like-dislike-button-view-model/yt'
                              '-smartimation/div/div/like-button-view-model/toggle-button-view-model/button')
                like_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, like_xpath))
                )
                if like_button:
                    print("like_button")
                    sleep(5)
                    like_button.click()
                    print(f'Like button found and clicked')

                if int(process_subscribe) < int(target_subscribe):
                    subscribe_button_selector = '#subscribe-button-shape > button'
                    subscribe_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, subscribe_button_selector))
                    )
                    if subscribe_button:
                        print(f'subscribe button found and clicked')
                        subscribe_button.click()
                        try:
                            collection_order.update_one(
                                {"video": object_id},
                                {"$set": {"process_subscribe": int(process_subscribe) + 1}}
                            )
                        except Exception as e:
                            print(f"Error occurred during database update: {str(e)}")
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
            elif action == 'dislike':
                dislike_button_selector = ('#top-level-buttons-computed > segmented-like-dislike-button-view-model > '
                                           'yt-smartimation > div > div > dislike-button-view-model > '
                                           'toggle-button-view-model > button')
                dislike_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, dislike_button_selector))
                )
                if dislike_button:
                    sleep(1)
                    print('Dislike button found and clicked')
                    dislike_button.click()
                    sleep(3)
            elif action == 'view':
                sleep(5)


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
        ips_data = list(collection_ips.find())
        ip_array = []
        for ip in ips_data:
            ip_array.append(ip.get("ip"))
        url = "https://accounts.google.com/v3/signin/identifier?authuser=0&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fdata&ec=GAlAFw&hl=en&service=mail&flowName=GlifWebSignIn&flowEntry=AddSession&dsh=S-1056250542%3A1700483692061719&theme=glif"
        driver = webdriver.Chrome(options=chrome_options)
        sleep(5)
        driver.get(url)
        sleep(2)
        try:
            username_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            sleep(2)
            username_input.send_keys(email)
            sleep(2)
            driver.find_element(By.ID, 'identifierNext').click()
            sleep(2)

            # Check if the email entered is not valid or not found
            try:
                invalid_email_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(text(), 'Could’t find your Google Account')]"))
                )
                if invalid_email_element:
                    try:
                        collection.update_one(
                            {"email": email},
                            {"$set": {"status": "Inactive"}}
                        )
                    except Exception as e:
                        print(f"Error occurred during database update: {str(e)}")
                    driver.quit()
                    print("Invalid email or email not found.")
                    return {"error": "Invalid email or email not found."}
            except:
                pass

            password_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "Passwd"))
            )
            sleep(2)
            password_input.send_keys(password)
            sleep(2)
            driver.find_element(By.ID, "passwordNext").click()

            # Check if the password entered is incorrect
            try:
                incorrect_password_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "//span[contains(text(), 'Wrong password. Try again or click "
                                                    "Forgot password to reset it.')]"))
                )
                if incorrect_password_element:
                    try:
                        collection.update_one(
                            {"email": email},
                            {"$set": {"status": "Inactive"}}
                        )
                    except Exception as e:
                        print(f"Error occurred during database update: {str(e)}")
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
                    try:
                        collection.update_one(
                            {"email": email},
                            {"$set": {"status": "Inactive"}}
                        )
                    except Exception as e:
                        print(f"Error occurred during database update: {str(e)}")
                    result_set = {"Verify it’s you."}
                    driver.quit()
                    return {"result": list(result_set)}

            except:
                pass

            print(f"Logged in successfully with {email} and Gmail is connected.")
            sleep(3)
            go_to_youtube_and_view_video_after_login(video_urls_array, driver)
            sleep(5)
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
        pending_orders = collection_order.find({"order_status": "pending"})
        # video_urls_array = get_video_links_for_pending_orders(pending_orders, collection_youtube)
        video_urls_array =["https://www.youtube.com/watch?v=JwbWqVznxTg"]
        emails_data_here = collection.find({"status": "active"}).skip(current_position).limit(limit)
        current_position += limit
        threads = []
        for email_data in emails_data_here:
            email = email_data["email"]
            password = email_data["password"]
            thread = Thread(target=login_to_gmail_and_store_driver, args=(email, password, video_urls_array))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
    else:
        return jsonify({"status": "error", "message": "Not connected to the network."})


# Without Login Functions
def open_youtube_video_without_login(driver, youtube_video_url):
    try:
        print("open try")
        driver.execute_script(f"window.open('{youtube_video_url}', '_blank');")
        result = collection_youtube.find_one({"video_link": youtube_video_url})
        if result:
            object_id = result.get('_id')
            if object_id:
                result_order = collection_order.find_one({"video": object_id})
                if result_order:
                    target_views = result_order.get('target_views')
                    process_views = result_order.get('process_views')
                    if int(process_views) < int(target_views):
                        try:
                            collection_order.update_one(
                                {"video": object_id},
                                {"$set": {"process_views": int(process_views) + 1}}
                            )
                            collection_order.update_one(
                                {"video": object_id},
                                {"$set": {"order_status": "pending"}}
                            )
                        except Exception as e:
                            print(f"Error occurred during database update: {str(e)}")
                    else:
                        print(f'video limit reached {target_views}')
                        collection_order.update_one(
                            {"video": object_id},
                            {"$set": {"order_status": "success"}}
                        )
                else:
                    print("No matching document found in collection_order for _id:", object_id)
        else:
            print("No document found in collection_youtube for video_link:", youtube_video_url)
    except Exception as ex:
        print(f"An unexpected error occurred: {str(ex)}")


def go_to_youtube_and_view_video_without_login(video_urls_array, driver):
    with app.app_context():
        if is_connected_to_network():
            try:
                for youtube_video_url in video_urls_array:
                    open_youtube_video_without_login(driver, youtube_video_url)

                for index, youtube_video_url in enumerate(video_urls_array):
                    driver.switch_to.window(driver.window_handles[index + 1])

                    try:
                        play_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CLASS_NAME, 'ytp-large-play-button'))
                        )
                        play_button.click()
                        print(f'play button clicked on tab {index + 1}')
                        sleep(2)
                    except TimeoutException:
                        print(f'Play button not found on tab {index + 1}. Skipping...')
                        continue

                result = collection_youtube.find_one({"video_link": youtube_video_url})
                if result:
                    half_length_of_video_from_database = int(result.get('half_length_in_second'))
                    full_length_of_video_from_database = int(result.get('full_length_in_second'))
                    object_id = result.get('_id')
                    if object_id:
                        result_order = collection_order.find_one({"video": object_id})
                        if result_order:
                            target_views = result_order.get('target_views')
                            process_views = result_order.get('process_views')

                            if int(process_views) < int(target_views):
                                random_number_of_video_watch = generate_random_number(
                                    half_length_of_video_from_database,
                                    full_length_of_video_from_database)
                                print("random Number", random_number_of_video_watch)
                                sleep(random_number_of_video_watch)
                            else:
                                print(f'video limit reached {target_views}')
                                collection_order.update_one(
                                    {"video": object_id},
                                    {"$set": {"order_status": "success"}}
                                )
                        else:
                            print("No matching document found in collection_order for _id:", object_id)
                else:
                    print("No document found in collection_youtube for video_link:", youtube_video_url)
                return jsonify({
                    "status": "success",
                    "message": "All videos opened successfully in separate tabs. Browser quit."
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


def login_to_gmail_and_store_driver_for_without_login(video_urls_array):
    with app.app_context():
        driver = webdriver.Chrome(options=chrome_options)
        sleep(2)
        try:
            go_to_youtube_and_view_video_without_login(video_urls_array, driver)
            driver.quit()
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error: {e}")

        finally:
            drivers.append(driver)


def login_to_gmail_with_limit_api_for_without_login(limit):
    print("without login part hre please call this ")
    global current_position

    if is_connected_to_network():
        threads = []
        pending_orders = collection_order.find({"order_status": "pending"})
        video_urls_array = get_video_links_for_pending_orders(pending_orders, collection_youtube)
        thread = Thread(target=login_to_gmail_and_store_driver_for_without_login, args=(video_urls_array,))
        threads.append(thread)
        thread.start()
        for thread in threads:
            thread.join()
        return jsonify({"status": "success", "message": f"Logged in to Gmail for the next {limit} accounts."})
    else:
        return jsonify({"status": "error", "message": "Not connected to the network."})


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




@app.route('/py_amit', methods=['GET'])
def py_amit():
    return jsonify({
        "status": "success",
        "message": "amit py hello."
    })



if __name__ == '__main__':
    app.run(debug=True, port=5000)
