import os
import time
import base64
import json
import requests
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.service import Service
from dotenv import load_dotenv
from selenium.webdriver.firefox.service import Service
import logging


with open("config_data.json", "r") as f:
    config = json.load(f)


# Get the absolute path to the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Path to the .env file
env_path = os.path.join(script_dir, '.env')
# Check if .env file exists
if not os.path.exists(env_path):
    print(f"ERROR: .env file not found at {env_path}.")
    print("Please create a .env file with the following content:")
    print("TRUECAPTCHA_USER=your_username_here")
    print("TRUECAPTCHA_KEY=your_api_key_here")
    # Use hardcoded credentials as fallback for testing - remove in production
    TRUECAPTCHA_USER = "your_username_here"
    TRUECAPTCHA_KEY = "your_api_key_here"
else:
    # Load TrueCaptcha credentials from .env file
    load_dotenv(dotenv_path=env_path)
    TRUECAPTCHA_USER = os.getenv("TRUECAPTCHA_USER")
    TRUECAPTCHA_KEY = os.getenv("TRUECAPTCHA_KEY")

# Print to help with debugging - we can remove this later
print(f"TrueCaptcha credentials loaded from {env_path}: User={TRUECAPTCHA_USER is not None}, Key={TRUECAPTCHA_KEY is not None}")

def solve_captcha(captcha_img):
    """
    Solve the captcha by taking a screenshot and using TrueCaptcha API.
    Args:
        captcha_img: The WebElement representing the captcha image
    Returns:
        str: The solved captcha text
    """
    # Check if credentials are available
    if not TRUECAPTCHA_USER or not TRUECAPTCHA_KEY:
        error_msg = "TrueCaptcha credentials are missing. Please check your .env file."
        print(error_msg)
        raise ValueError(error_msg)
    
    # Create screenshots directory if it doesn't exist
    os.makedirs("screenshots", exist_ok=True)
    captcha_path = os.path.join("screenshots", "captcha.png")
    
    # Take screenshot of the captcha
    captcha_img.screenshot(captcha_path)
    
    # Base64-encode the screenshot
    with open(captcha_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    # Send to TrueCaptcha API
    resp = requests.post(
        "https://api.apitruecaptcha.org/one/gettext",
        json={"userid": TRUECAPTCHA_USER, "apikey": TRUECAPTCHA_KEY, "data": b64}
    )
    resp.raise_for_status()
    
    # Return the solved captcha text
    return resp.json().get("result", "").strip()


def initialize_browser(firefox_profile_path):
    """
    Initialize Firefox browser with specified profile path
    Args:
        firefox_profile_path: Path to the Firefox profile to use
    Returns:
        WebDriver: Initialized Firefox WebDriver instance
    """
    print(f"Initializing browser with profile: {firefox_profile_path}")
    firefox_options = Options()
    if os.path.exists(firefox_profile_path):
        print(f"Using existing Firefox profile: {firefox_profile_path}")
        firefox_options.add_argument('-profile')
        firefox_options.add_argument(firefox_profile_path)
    else:
        print(f"Profile not found at {firefox_profile_path}")
        print("Using a new profile instead.")
    
    # Automatically download and set up geckodriver
    try:
        print("Setting up geckodriver using webdriver-manager...")
        driver_path = GeckoDriverManager().install()
        print(f"Geckodriver installed at: {driver_path}")
        
        # Initialize the driver with the Service object
        service = Service(driver_path)
        driver = webdriver.Firefox(service=service, options=firefox_options)
        driver.maximize_window()
        return driver
    except Exception as e:
        print(f"Error setting up geckodriver: {e}")
        raise


def perform_login(driver=None, close_after_login=False):
    """
    Perform login to MCA portal.
    Args:
        driver: Existing WebDriver instance (optional). If not provided, will create a new one.
        close_after_login: Whether to close the browser after login.
    Returns:
        tuple: (driver, success) where driver is the WebDriver instance and success is a boolean
               indicating if login was successful
    """
    own_driver = driver is None
    try:
        # Load profile path from config_data.json
        with open("config_data.json", "r") as f:
            config = json.load(f)
        
        # Initialize browser if needed
        if own_driver:
            firefox_profile_path = config["firefox_profile_path"]
            driver = initialize_browser(firefox_profile_path)
        
        # First try to access Fillip page directly
        fillip_url = "https://www.mca.gov.in/content/mca/global/en/mca/e-filing/annual-filings/form-aoc4.html"
        print("\nAttempting to access Fillip page directly...")
        driver.get(fillip_url)
        
        # Wait for page to load
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # Check if we're already logged in
        try:
            time.sleep(5)
            current_url = driver.current_url
            
            if fillip_url in current_url:
                print("\n" + "="*50)
                print("ALREADY LOGGED IN! ACCESSING FILLIP PAGE DIRECTLY.")
                print("="*50 + "\n")
                return driver, True
            else:
                print("Not logged in. Proceeding with login process...")
        except Exception as e:
            print(f"Error checking login status: {e}")
            print("Proceeding with login process...")
        
        # Navigate to login page
        print("\nNavigating to login page...")
        driver.get("https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html")
        
        # Wait for page to load completely
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        print("Page load completed")
        time.sleep(5)  # Additional wait for dynamic content
        
        # Handle the dialog box
        print("Looking for dialog box...")
        try:
            ok_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@class='btn btn-primary' and @data-dismiss='modal' and contains(text(), 'OK')]"))
            )
            print("Dialog found. Clicking OK button...")
            ok_button.click()
            time.sleep(2)
            print("Dialog closed successfully")
        except Exception as e:
            print(f"No dialog detected or couldn't click OK button: {e}")
            print("Continuing with login process...")
        
        # Wait for login form
        print("Waiting for login form...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form"))
        )
        
        # Fill in User ID
        print("Entering user ID...")
        user_field = None
        for selector in [
            "//input[@type='text']",
            "//input[contains(@placeholder,'User ID')]",
            "//input[contains(@name,'userId')]",
            "//input[@id='userId']",
            "//input[@class='form-control']"
        ]:
            try:
                user_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if user_field.is_displayed() and user_field.is_enabled():
                    user_field.clear()
                    user_field.send_keys(config["user_email"])
                    print("User ID entered successfully")
                    break
            except:
                continue
        
        if not user_field:
            raise Exception("Could not find user ID field")
        
        # Fill in Password
        print("Entering password...")
        try:
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_field.clear()
            password_field.send_keys(config["user_password"])
            print("Password entered successfully")
        except Exception as e:
            raise Exception(f"Could not find or interact with password field: {e}")
        
        # Set expected successful URL
        expected_url = fillip_url
        max_attempts = 10
        attempt = 1
        login_success = False
        
        # Loop until successful login or max attempts reached
        while attempt <= max_attempts and not login_success:
            print(f"\nCaptcha attempt {attempt}/{max_attempts}")
            
            # Find and solve the captcha
            print("Locating captcha image...")
            try:
                # Try multiple selectors for captcha image
                captcha_selectors = [
                    "img[src*='captcha']",
                    "img[alt*='captcha']",
                    "img[class*='captcha']",
                    "img[src*='Captcha']",
                    "img[alt*='Captcha']",
                    "img[class*='Captcha']"
                ]
                
                captcha_img = None
                for selector in captcha_selectors:
                    try:
                        captcha_img = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if captcha_img.is_displayed():
                            print(f"Found captcha image using selector: {selector}")
                            break
                    except:
                        continue
                
                if not captcha_img:
                    raise Exception("Could not find visible captcha image")
                
            except Exception as e:
                print(f"Error finding captcha image: {e}")
                attempt += 1
                continue
            
            # Solve the captcha
            print("Solving captcha...")
            try:
                captcha_text = solve_captcha(captcha_img)
                print(f"Captcha solved: {captcha_text}")
            except Exception as e:
                print(f"Error solving captcha: {e}")
                attempt += 1
                continue
            
            # Enter the solved captcha
            print("Entering captcha solution...")
            try:
                captcha_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "customCaptchaInput"))
                )
                captcha_field.clear()
                captcha_field.send_keys(captcha_text)
                print("Captcha entered successfully")
            except Exception as e:
                print(f"Error entering captcha: {e}")
                attempt += 1
                continue
            
            # Click Login button
            print("Clicking login button...")
            try:
                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Login') or @type='submit']"))
                )
                login_button.click()
                print("Login button clicked")
                
                # Wait for navigation and check for successful login
                print("Waiting for login response...")
                time.sleep(5)

                # Check if we've been redirected to Application History URL
                application_history_url = "https://www.mca.gov.in/content/mca/global/en/application-history.html"
                current_url = driver.current_url
                if application_history_url in current_url:
                    login_success = True
                    print("\n" + "="*50)
                    print("LOGIN SUCCESSFUL! Redirected to Application History page.")
                    print(f"Current URL: {current_url}")
                    print("="*50 + "\n")
                    print("Redirecting to Fillip page...")
                    driver.get(fillip_url)
                    WebDriverWait(driver, 20).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                    print("Redirected to Fillip page after Application History page.")
                    # Double-check if now on Fillip page
                    if fillip_url in driver.current_url:
                        print("\n" + "="*50)
                        print("SUCCESSFULLY REDIRECTED TO FILLIP PAGE!")
                        print(f"Current URL: {driver.current_url}")
                        print("="*50 + "\n")
                        return driver, True
                    else:
                        print(f"\nWarning: Not on Fillip page after redirect. Current URL: {driver.current_url}")
                        return driver, False
                elif fillip_url in current_url:
                    login_success = True
                    print("\n" + "="*50)
                    print("LOGIN SUCCESSFUL! Already on Fillip page.")
                    print(f"Current URL: {current_url}")
                    print("="*50 + "\n")
                    return driver, True
                # If not redirected, check for error message
                else:
                    try:
                        error_msg = driver.find_element(By.CSS_SELECTOR, ".alert-danger")
                        print(f"Login failed. Error message: {error_msg.text}")
                    except:
                        print("Login failed. No specific error message found.")

                    # Only try to refresh captcha if login failed and we haven't reached max attempts
                    if attempt < max_attempts:
                        print("Refreshing captcha for next attempt...")
                        try:
                            refresh_button = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.ID, "refresh-img"))
                            )
                            refresh_button.click()
                            print("Captcha refreshed successfully")
                            time.sleep(2)
                        except Exception as e:
                            print(f"Error refreshing captcha: {e}")
                            # Do not refresh the page, just log and continue

                    attempt += 1
                    if attempt <= max_attempts:
                        print("Retrying with a new captcha...")
                        time.sleep(2)
            except Exception as e:
                print(f"Error during login attempt: {e}")
                attempt += 1
                continue
        
        if not login_success:
            print(f"Failed to login after {max_attempts} attempts.")
            return driver, False
        
        # After successful login, verify we're on Fillip page or Application History page
        current_url = driver.current_url
        application_history_url = "https://www.mca.gov.in/content/mca/global/en/application-history.html"
        if fillip_url in current_url:
            print("\n" + "="*50)
            print("SUCCESSFULLY ON FILLIP PAGE!")
            print(f"Current URL: {current_url}")
            print("="*50 + "\n")
            return driver, True
        elif "/application-history.html" in current_url:
            print("\nDetected Application History page after login. Login successful!")
            print(f"Current URL: {current_url}")
            print("Redirecting to Fillip page...")
            driver.get(fillip_url)
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            print("Redirected to Fillip page after Application History page.")
            # Double-check if now on Fillip page
            if fillip_url in driver.current_url:
                print("\n" + "="*50)
                print("SUCCESSFULLY REDIRECTED TO FILLIP PAGE!")
                print(f"Current URL: {driver.current_url}")
                print("="*50 + "\n")
                return driver, True
            else:
                print(f"\nWarning: Not on Fillip page after redirect. Current URL: {driver.current_url}")
                return driver, False
        else:
            print(f"\nWarning: Not on Fillip or Application History page. Current URL: {current_url}")
            return driver, False
            
    except Exception as e:
        print(f"Error during process: {e}")
        return driver, False
    finally:
        # Close the browser if requested and we created it
        if close_after_login and own_driver and driver:
            print("Closing browser as requested.")
            driver.quit()
            return None, False

def main():
    """
    Main workflow function that:
    1. Handles login
    2. After successful login, directly runs LLP Registration form automation
    """
    print("\n" + "="*50)
    print("STARTING MCA AUTOMATION WORKFLOW")
    print("="*50 + "\n")
    
    # Step 1: Load configuration
    try:
        with open("config_data.json", "r") as f:
            config = json.load(f)
        print("Configuration loaded successfully")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Creating default configuration")
        config = {
            "firefox_profile_path": os.path.join(os.path.expanduser("~"), 
                                              "AppData", "Roaming", "Mozilla", "Firefox", "Profiles"),
            "fillip_url": "https://www.mca.gov.in/content/mca/global/en/mca/llp-e-filling/Fillip.html"
        }
        with open("config_data.json", "w") as f:
            json.dump(config, f, indent=4)
    
    # Step 2: Perform login
    print("\nStep 1: Performing login...")
    driver, login_success = perform_login(close_after_login=False)
    
    # Step 3: If login successful, proceed with automation
    if login_success:
        print("\nStep 2: Login successful. Proceeding with automation...")
        try:
            # Wait for page to fully load
            time.sleep(5)
            
            # Run the LLP Registration form automation directly
            print("\n" + "="*50)
            print("STARTING LLP REGISTRATION FORM AUTOMATION")
            print("="*50)
            
            # Initialize automate1 with our driver
            automate1.setup_driver(driver)
            
            # Run the LLP form sequence
            success = automate1.run_llp_form_sequence(driver)
            
            if success:
                print("\n" + "="*50)
                print("AUTOMATION COMPLETED SUCCESSFULLY!")
                print("="*50 + "\n")
            else:
                print("\n" + "="*50)
                print("AUTOMATION COMPLETED WITH ERRORS!")
                print("Some steps may not have completed successfully.")
                print("="*50 + "\n")
            
        except Exception as e:
            print(f"\nError during automation: {e}")
            print("\n" + "="*50)
            print("AUTOMATION FAILED!")
            print("Please check the error messages above.")
            print("="*50 + "\n")
    else:
        print("\n" + "="*50)
        print("LOGIN FAILED! Cannot continue with automation.")
        print("Please check the error messages above.")
        print("="*50 + "\n")
    
    # Prompt user to close or keep browser open
    if 'driver' in locals() and driver:
        user_input = input("Press Enter to close the browser, or type anything and press Enter to keep it open: ")
        if user_input.strip() == "":
            print("Closing browser...")
            try:
                driver.quit()
                print("Browser closed.")
            except Exception as e:
                print(f"Error closing browser: {e}")
        else:
            print("Keeping browser open. You can continue manually.")


if __name__ == "__main__":
    main()


