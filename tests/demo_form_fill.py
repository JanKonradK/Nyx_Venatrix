"""
Simple Playwright demonstration - fills the simulation form
This bypasses the AI agent to demonstrate the basic automation working
"""
from playwright.sync_api import sync_playwright
import time

def fill_test_form():
    print("🎭 Starting Playwright Form Filler Demo...")

    with sync_playwright() as p:
        print("📂 Launching browser...")
        browser = p.chromium.launch(headless=False, slow_mo=500)  # Visible browser, slow for demo
        context = browser.new_context()
        page = context.new_page()

        print("🌐 Navigating to form...")
        page.goto("http://localhost:8081/tests/simulation_target.html")

        print("📝 Filling form fields...")

        # Fill the form
        page.fill("#full_name", "John Doe")
        print("  ✅ Filled: Full Name")

        page.fill("#email", "john.doe@example.com")
        print("  ✅ Filled: Email")

        page.fill("#phone", "+1-555-0123")
        print("  ✅ Filled: Phone")

        page.fill("#linkedin", "https://linkedin.com/in/johndoe")
        print("  ✅ Filled: LinkedIn")

        page.select_option("#experience", "5+")
        print("  ✅ Selected: Experience Level")

        page.fill("#cover_letter", "I am very interested in this position and believe my skills in Python, TypeScript, and distributed systems make me a great fit for this role.")
        print("  ✅ Filled: Cover Letter")

        page.check("input[name='terms']")
        print("  ✅ Checked: Terms and Conditions")

        print("\n✨ Form filled successfully!")
        print("⏸️  Pausing for 3 seconds so you can see the filled form...")
        time.sleep(3)

        print("🚀 Submitting form...")
        page.click("button[type='submit']")

        # Wait for success message
        page.wait_for_selector("#success-message", state="visible", timeout=5000)

        print("✅ SUCCESS! Form submitted successfully!")
        print("📸 Success message visible on page")

        time.sleep(2)

        browser.close()
        print("🎉 Demo complete!")

if __name__ == "__main__":
    fill_test_form()
