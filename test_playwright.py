from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
    page = browser.new_page()
    page.goto("http://127.0.0.1:5173/knowledge-base")
    page.wait_for_load_timeout(3000)
    print("Page title:", page.title())
    print("Page content snippet:", page.content()[:1000])
    
    # Check if login form appears
    if "Sign in" in page.content() or "Alex" in page.content() or page.get_by_text("Sign in").is_visible():
        print("Login form detected")
        try:
            page.get_by_role("button", name="Alex").click()
        except:
            pass
        page.wait_for_load_timeout(2000)
        
    page.goto("http://127.0.0.1:5173/knowledge-base")
    page.wait_for_load_timeout(3000)
    
    # Scroll or find 'sources' card named 'notes'
    print("Looking for 'notes' source card...")
    content = page.content()
    print("Has 'notes':", "notes" in content)
    print("Has 'Copy Recent Notes':", "Copy Recent Notes" in content)
    
    browser.close()
