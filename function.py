import time
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    NoSuchElementException,
    ElementClickInterceptedException
)

# --- Basic Logger Setup ---
# In a real project, you would configure this more extensively.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def input_text(driver: WebDriver, locator: tuple, text: str, timeout: int = 15, clear_first: bool = True):
    """
    Safely finds an element, clears it, and inputs text with multiple fallbacks.

    This function incorporates best practices from the analyzed script:
    1.  Waits for any loading overlays to disappear.
    2.  Waits for the specific input field to be present, visible, and clickable.
    3.  Scrolls the element into the center of the view to ensure it's not off-screen.
    4.  Attempts a standard clear() and send_keys() action.
    5.  If the element is disabled or readonly, it uses JavaScript to enable it and set the value.
    6.  If any other interaction error occurs, it falls back to a pure JavaScript value set.
    7.  Triggers 'input' and 'change' events to ensure frameworks like React/Angular detect the change.

    Args:
        driver: The Selenium WebDriver instance.
        locator: A tuple containing the locator strategy and value (e.g., (By.ID, "my-id")).
        text: The text to input into the field.
        timeout: The maximum time in seconds to wait for the element.
        clear_first: Whether to clear the field before inputting text.

    Returns:
        True if the text was successfully input, False otherwise.
    """
    logger.info(f"Attempting to input text into element located by {locator}")
    try:
        # 1. Wait for overlays to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "dimmer-holder"))
        )

        # 2. Wait for the element to be ready for interaction
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )

        # 3. Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
        time.sleep(0.5) # Brief pause for scrolling to finish

        # 4. Check if element is disabled or readonly
        if not element.is_enabled() or element.get_attribute("readonly"):
            logger.warning(f"Element {locator} is not interactable. Attempting JavaScript fallback.")
            driver.execute_script("arguments[0].readOnly = false;", element)
            driver.execute_script("arguments[0].disabled = false;", element)
            driver.execute_script("arguments[0].value = arguments[1];", element, text)
        else:
            # 5. Standard interaction
            if clear_first:
                element.clear()
            element.send_keys(text)

        # 6. Trigger events to notify JS frameworks of the change
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", element)

        logger.info(f"Successfully input text into element {locator}")
        return True

    except TimeoutException:
        logger.error(f"Timeout: Element {locator} was not found or clickable within {timeout} seconds.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while inputting text into {locator}: {e}")
        # Final fallback using JavaScript
        try:
            logger.info("Attempting final JavaScript fallback to set value.")
            element = driver.find_element(*locator)
            driver.execute_script("arguments[0].value = arguments[1];", element, text)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
            logger.info(f"Successfully input text into element {locator} via final JS fallback.")
            return True
        except Exception as js_e:
            logger.error(f"All input methods failed for {locator}: {js_e}")
            return False


def click_element(driver: WebDriver, locator: tuple, timeout: int = 15):
    """
    Safely clicks an element with waits, retries, and a JavaScript fallback.

    This function incorporates best practices from the analyzed script:
    1.  Waits for any loading overlays to disappear.
    2.  Waits for the element to be stable and clickable.
    3.  Scrolls the element into view.
    4.  Attempts a standard .click().
    5.  If the click is intercepted, it falls back to a JavaScript click.

    Args:
        driver: The Selenium WebDriver instance.
        locator: A tuple containing the locator strategy and value (e.g., (By.XPATH, "//button")).
        timeout: The maximum time in seconds to wait for the element.

    Returns:
        True if the element was successfully clicked, False otherwise.
    """
    logger.info(f"Attempting to click element located by {locator}")
    try:
        # 1. Wait for overlays to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "dimmer-holder"))
        )

        # 2. Wait for element to be clickable
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )

        # 3. Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
        time.sleep(0.5) # Brief pause for stability

        # 4. Standard click
        element.click()
        logger.info(f"Successfully clicked element {locator} using standard method.")
        return True

    except ElementClickInterceptedException:
        logger.warning(f"Standard click was intercepted for {locator}. Attempting JavaScript click.")
        try:
            # 5. JavaScript fallback click
            element = driver.find_element(*locator) # Re-find element
            driver.execute_script("arguments[0].click();", element)
            logger.info(f"Successfully clicked element {locator} using JavaScript fallback.")
            return True
        except Exception as e:
            logger.error(f"JavaScript click also failed for {locator}: {e}")
            return False
    except TimeoutException:
        logger.error(f"Timeout: Element {locator} was not found or clickable within {timeout} seconds.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while clicking {locator}: {e}")
        return False


def click_checkbox(driver: WebDriver, locator: tuple, desired_state: bool = True, timeout: int = 15):
    """
    Safely clicks a checkbox to ensure it is in the desired state (checked or unchecked).

    Args:
        driver: The Selenium WebDriver instance.
        locator: A tuple containing the locator strategy and value.
        desired_state: True to check the box, False to uncheck it.
        timeout: The maximum time in seconds to wait for the element.

    Returns:
        True if the checkbox is in the desired state after the operation, False otherwise.
    """
    logger.info(f"Attempting to set checkbox {locator} to state: {desired_state}")
    try:
        # Wait for the checkbox to be present
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        
        # Scroll to the element
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
        time.sleep(0.5)

        # Check the current state and click only if necessary
        if element.is_selected() != desired_state:
            logger.info(f"Checkbox is not in desired state. Clicking to change.")
            # Use the robust click_element function to perform the click
            if not click_element(driver, locator, timeout):
                # If click_element fails, we can't proceed
                logger.error(f"Failed to click the checkbox {locator}.")
                return False
        else:
            logger.info(f"Checkbox {locator} is already in the desired state.")

        # Final verification
        final_state = driver.find_element(*locator).is_selected()
        if final_state == desired_state:
            logger.info(f"SUCCESS: Checkbox {locator} is now in state: {final_state}")
            return True
        else:
            logger.error(f"FAILURE: Checkbox {locator} is in state {final_state}, but expected {desired_state}.")
            return False

    except TimeoutException:
        logger.error(f"Timeout: Checkbox {locator} was not found within {timeout} seconds.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred with checkbox {locator}: {e}")
        return False


def select_dropdown_option(driver: WebDriver, locator: tuple, option_text: str, by: str = "visible_text", timeout: int = 15):
    """
    Safely selects an option from a <select> dropdown menu.

    Args:
        driver: The Selenium WebDriver instance.
        locator: A tuple for the <select> element locator.
        option_text: The text (or value) of the option to select.
        by: The method to select the option by. Can be "visible_text", "value", or "index".
        timeout: The maximum time in seconds to wait for the element.

    Returns:
        True if the option was successfully selected, False otherwise.
    """
    logger.info(f"Attempting to select '{option_text}' from dropdown {locator}")
    try:
        # Wait for the dropdown element to be present
        dropdown_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        
        # Scroll to the dropdown
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", dropdown_element)
        time.sleep(0.5)

        # Use Selenium's Select class for robust interaction
        select = Select(dropdown_element)

        if by == "visible_text":
            select.select_by_visible_text(option_text)
        elif by == "value":
            select.select_by_value(option_text)
        elif by == "index":
            select.select_by_index(int(option_text))
        else:
            logger.error(f"Invalid selection method '{by}'. Use 'visible_text', 'value', or 'index'.")
            return False

        # Verification
        selected_option = select.first_selected_option.text.strip()
        logger.info(f"Successfully selected. Current value: '{selected_option}'")
        return True

    except NoSuchElementException:
        logger.error(f"Option '{option_text}' not found in dropdown {locator}.")
        # Log available options for easier debugging
        try:
            all_options = [opt.text for opt in Select(driver.find_element(*locator)).options]
            logger.info(f"Available options are: {all_options}")
        except:
            pass
        return False
    except TimeoutException:
        logger.error(f"Timeout: Dropdown {locator} was not found within {timeout} seconds.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred with dropdown {locator}: {e}")
        return False
