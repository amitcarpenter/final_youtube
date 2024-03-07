from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep



def click_video_by_title(driver, keyword):
    try:
        # Wait for the video titles to be present on the page
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "style-scope ytd-video-renderer"))
        )

        # Find all elements with the specified class (assuming they are video titles)
        video_titles = driver.find_elements(By.CSS_SELECTOR, "#video-title > yt-formatted-string")

        for title_element in video_titles:
            # Get the text content of the title element
            title_text = title_element.text

            # Check if the keyword is present in the title
            if keyword.lower() in title_text.lower():
                print(f"Found matching title: {title_text}")
                
                # Click on the matching title element
                title_element.click()
                
                # You can add additional actions after clicking on the title if needed

                # Break the loop since we found and clicked on the desired title
                break

    except Exception as e:
        print(f"An error occurred: {e}")




def youtube_automation(keyword):
    # Your webdriver setup (e.g., Chrome)
    driver = webdriver.Chrome()
    try:
        driver.get("https://www.youtube.com/")
        sleep(10)
        search_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='search']"))
        )
        # search_box = driver.find_element("xpath", "//input[@id='search']")
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)
        sleep(5)
        click_video_by_title(driver, keyword)

        sleep(1000)

        # You can perform additional actions on the video page if needed

    finally:
        # Close the browser window
        driver.quit()

# Example usage
keyword_to_search = "#bed 6x4 ka folding wooden 18mm kishmish //@mein bed furniture m.s carpenter faridabad &#"
youtube_automation(keyword_to_search)
