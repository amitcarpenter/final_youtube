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


@app.route('/check_video_duration', methods=['POST'])
def check_video_duration_api():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Invalid request format. JSON expected."})
    data = request.get_json()
    video_url = data.get('video_url')
    if not video_url:
        return jsonify({"status": "error", "message": "Missing 'video_url' parameter."})
    if is_connected_to_network():
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        driver.get(video_url)
        sleep(1)
        page_source = driver.page_source
        driver.quit()

        soup = BeautifulSoup(page_source, 'html.parser')
        subscriber_count_element = soup.find('yt-formatted-string', id='owner-sub-count')
        duration_element = soup.find('span', class_='ytp-time-duration')
        channel_name_element = soup.find('yt-formatted-string', class_='style-scope ytd-channel-name')

        if duration_element and subscriber_count_element and channel_name_element:
            video_duration_str, hours, minutes, seconds, total_seconds, half_seconds_rounded = convert_duration_to_seconds_and_round(
                duration_element.text)
            print(video_duration_str, hours, minutes, seconds, total_seconds, half_seconds_rounded)
            subscriber_count_text = subscriber_count_element.text
            trimmed_text = subscriber_count_text.split()[0]
            channel_name = channel_name_element.text.strip()
            return jsonify({
                "status": "success",
                "video_duration": video_duration_str,
                "total_seconds": total_seconds,
                "half_seconds_rounded": half_seconds_rounded,
                "subscriber_count": trimmed_text,
                "channel_name": channel_name,
            })

        else:
            return jsonify({"status": "error", "message": "Unable to find video duration element."})
    else:
        return jsonify({"status": "error", "message": "Not connected to the network."})


def process_video_data(video_info):
    youtube_video_url = video_info.get("video_link")
    youtube_video_views_target = video_info.get("target_views")

    return {
        "youtube_video_url": youtube_video_url,
        "youtube_video_views_target": youtube_video_views_target,
    }


current_action = 'like'
process_subscribe = 0 


# With Login
def perform_like_action(driver, action, target_likes, target_subscribe):
    try:
        for _ in range(1): 
            print(action)
            print(target_likes , "target LIkes")
            print(target_subscribe , "target subscribe")
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
                    
                if int(process_subscribe) < int(target_subscribe):
                    subscribe_button_selector = '#subscribe-button-shape > button'
                    subscribe_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, subscribe_button_selector))
                    )
                    if subscribe_button:
                        print(f'subscribe button found and clicked')
                        subscribe_button.click()
                        process_subscribe +=1
                        print(f"process subscribe {process_subscribe}")
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
                        sleep(10)
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


def open_youtube_video(driver, youtube_video_url, target_likes, target_subscribe):
    global current_action
    driver.execute_script(f"window.open('{youtube_video_url}', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    try:
        perform_like_action(driver, "like", target_likes, target_subscribe)
    except TimeoutException:
        print(f'Timeout: {current_action.capitalize()} button not found')
    except NoSuchElementException:
        print(f'Element not found: {current_action.capitalize()} button not present on the page')
    driver.switch_to.window(driver.window_handles[0])


def go_to_youtube_and_view_video_after_login(video_urls_array, driver,  target_likes, target_subscribe):
    with app.app_context():
        if is_connected_to_network():
            try:
                for youtube_video_url in video_urls_array:
                    open_youtube_video(driver, youtube_video_url, target_likes, target_subscribe)
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


def go_to_youtube_and_search_keyword_by_channel(video_keyword, driver,  target_likes, target_subscribe):
    global current_action
    youtube_url = "https://www.youtube.com/"
    driver.execute_script(f"window.open('{youtube_url}', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    try:
        search_box = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='search']"))
        )
        search_box.send_keys(video_keyword)
        search_box.send_keys(Keys.RETURN)
        sleep(5)
        click_video_by_title(driver, video_keyword)
        sleep(4)
        print("after the clicking vidoe")
        perform_like_action(driver, "like", target_likes, target_subscribe)
    except TimeoutException:
        print(f'Timeout: {current_action.capitalize()} button not found')
    except NoSuchElementException:
        print(f'Element not found: {current_action.capitalize()} button not present on the page')
    driver.switch_to.window(driver.window_handles[0])


def login_to_gmail_and_store_driver(email, password, video_urls_array, target_likes, target_subscribe, video_keyword):
    with app.app_context():
        url = "https://accounts.google.com/v3/signin/identifier?authuser=0&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fdata&ec=GAlAFw&hl=en&service=mail&flowName=GlifWebSignIn&flowEntry=AddSession&dsh=S-1056250542%3A1700483692061719&theme=glif"
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
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
            sleep(3)
            
            if video_keyword is None:
                go_to_youtube_and_view_video_after_login(video_urls_array, driver,  target_likes, target_subscribe)
            else:
                go_to_youtube_and_search_keyword_by_channel(video_keyword, driver,  target_likes, target_subscribe)
                driver.quit()
                
            sleep(5)
            driver.quit()
        except (TimeoutException, NoSuchElementException) as e:
            driver.quit()
        finally:
            drivers.append(driver)


def login_to_gmail_with_limit_api(limit, video_urls_array, target_likes, target_subscribe, video_keyword):
    global current_position
    if is_connected_to_network():
        emails_data_here = collection.find().skip(current_position).limit(limit)
        current_position += limit
        threads = []
        for email_data in emails_data_here:
            email = email_data["email"]
            password = email_data["password"]
            thread = Thread(target=login_to_gmail_and_store_driver, args=(email, password, video_urls_array,  target_likes, target_subscribe, video_keyword))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
    else:
        return jsonify({"status": "error", "message": "Not connected to the network."})


# Without Login Functions
def open_youtube_video_without_login(driver, youtube_video_url):
    try:
        driver.execute_script(f"window.open('{youtube_video_url}', '_blank');")
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
                
                sleep(time_duration_in_second)
            except Exception as e:
                print("without login search")
        else:
            return jsonify({
                "status": "error",
                "message": "Not connected to the network."
            })


def click_video_by_title(driver, keyword):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "style-scope ytd-video-renderer"))
        )
        video_titles = driver.find_elements(By.CSS_SELECTOR, "#video-title > yt-formatted-string")

        for title_element in video_titles:
            title_text = title_element.text
            if keyword.lower() in title_text.lower():
                print(f"Found matching title: {title_text}")
                title_element.click()
                sleep(time_duration_in_second)
                print("sleep time complete")
    except Exception as e:
        print(f"An error occurred: {e}")


def go_to_youtube_and_view_video_without_login_with_search_keyword(driver,video_keyword):
    with app.app_context():
        if is_connected_to_network():
            try:
                print("try case")
                driver.get("https://www.youtube.com/")
                search_box = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@id='search']"))
                )
                search_box.send_keys(video_keyword)
                search_box.send_keys(Keys.RETURN)
                sleep(5)
                click_video_by_title(driver, video_keyword)
            except Exception as e:
                print("error! search by keyword without login")

        else:
            return jsonify({
                "status": "error",
                "message": "Not connected to the network."
            })


def login_to_gmail_and_store_driver_for_without_login(video_urls_array, video_keyword):
    with app.app_context():
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        sleep(2)
        try:
            if video_keyword is None:
                go_to_youtube_and_view_video_without_login(video_urls_array, driver)
                driver.quit()
            else:
                print("without else keywords")
                go_to_youtube_and_view_video_without_login_with_search_keyword(driver,video_keyword)
                driver.quit()
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error: {e}")

        finally:
            drivers.append(driver)


def login_to_gmail_with_limit_api_for_without_login(limit, video_keyword, video_urls_array):
    print("without login part hre please call this ")
    global current_position
    if is_connected_to_network():
        threads = []
        thread = Thread(target=login_to_gmail_and_store_driver_for_without_login, args=(video_urls_array, video_keyword))
        threads.append(thread)
        thread.start()
        for thread in threads:
            thread.join()
        return jsonify({"status": "success", "message": f"Logged in to Gmail for the next {limit} accounts."})
    else:
        return jsonify({"status": "error", "message": "Not connected to the network."})


@app.route('/go_to_youtube_and_view_video', methods=['POST'])
def go_to_youtube_and_view_video():
    global time_duration_in_second
    data = request.get_json()
    video_urls_array = data.get('video_urls_array')
    target_likes = data.get('target_likes')
    target_views = data.get('target_views')
    target_subscribe = data.get('target_subscribe')
    limit = data.get('browser_limit')
    video_keyword = data.get("video_keyword")
    time_duration_in_second = data.get("time_duration_in_second")
    emails_data = list(collection.find())
    emails_only_length = len(emails_data)
    print(f"Number of documents in the database Email: {emails_only_length}")
    
    if target_views:
        if is_connected_to_network():
            views_count = 0
            while views_count < target_views:
                if views_count < emails_only_length:
                    login_to_gmail_with_limit_api(limit, video_urls_array, target_likes, target_subscribe, video_keyword)
                    views_count += limit
                    print(views_count)
                else:
                    try:
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            tasks = [
                                executor.submit(login_to_gmail_with_limit_api_for_without_login, limit, video_keyword, video_urls_array)
                                for _ in range(limit)
                            ]
                            concurrent.futures.wait(tasks)
                        views_count += limit
                        print(views_count)
                    except Exception as e:
                        pass
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
