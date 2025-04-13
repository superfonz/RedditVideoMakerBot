import json

from pathlib import Path
import re
from time import sleep
from typing import Dict
from utils import settings
from playwright.async_api import async_playwright  # pylint: disable=unused-import

# do not remove the above line

from playwright.sync_api import sync_playwright, ViewportSize
from rich.progress import track
import translators as ts

from utils.console import print_step, print_substep


def download_screenshots_of_reddit_posts(reddit_object: dict, screenshot_num: int):
    """Downloads screenshots of reddit posts as seen on the web. Downloads to assets/temp/png

    Args:
        reddit_object (Dict): Reddit object received from reddit/subreddit.py
        screenshot_num (int): Number of screenshots to download
    """
    print_step("Downloading screenshots of reddit posts...")
    id = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])
    # ! Make sure the reddit screenshots folder exists
    Path(f"assets/temp/{id}/png").mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print_substep("Launching Headless Browser...")

        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        if settings.config["settings"]["theme"] == "dark":
            cookie_file = open("./video_creation/data/cookie-dark-mode.json", encoding="utf-8")
        else:
            cookie_file = open("./video_creation/data/cookie-light-mode.json", encoding="utf-8")
        cookies = json.load(cookie_file)
        context.add_cookies(cookies)  # load preference cookies
        # Get the thread screenshot
        page = context.new_page()
        print(reddit_object["thread_url"])
        page.goto(reddit_object["thread_url"], timeout=0)
        page.set_viewport_size(ViewportSize(width=1920, height=1080))

        if page.locator('[data-testid="content-gate"]').is_visible():
            # This means the post is NSFW and requires to click the proceed button.

            print_substep("Post is NSFW. You are spicy...")
            page.locator('[data-testid="content-gate"] button').click()
            page.wait_for_load_state()  # Wait for page to fully load

            if page.locator('[data-click-id="text"] button').is_visible():
                page.locator(
                    '[data-click-id="text"] button'
                ).click()  # Remove "Click to see nsfw" Button in Screenshot

        # translate code

        if settings.config["reddit"]["thread"]["post_lang"]:
            print_substep("Translating post...")
            texts_in_tl = ts.google(
                reddit_object["thread_title"],
                to_language=settings.config["reddit"]["thread"]["post_lang"],
            )

            page.evaluate(
                "tl_content => document.querySelector('[data-test-id=\"post-content\"] > div:nth-child(3) > div > div').textContent = tl_content",
                texts_in_tl,
            )
        else:
            print_substep("Skipping translation...")
        postcontentpath = f"assets/temp/{id}/png/title.png"

        for attempt in range(5):
            try:
                try:
                    page.wait_for_selector('button[data-testid="secondary-button"]', timeout=5000)
                    page.click('button[data-testid="secondary-button"]')
                    sleep(1)
                    page.wait_for_selector('button.button-small >> text="View NSFW content"', timeout=5000)
                    page.click('button.button-small >> text="View NSFW content"')
                    # page.wait_for_selector(f'[id="t3_{id}-read-more-button"]', timeout=5000)
                    # page.click(f'[id="t3_{id}-read-more-button"]')
                except Exception as e:
                    print_substep("NSFW Buttons not found, skipping...", style="bold green")
                sleep(1)
                if settings.config["settings"]["story_text"]["small_tile"]:
                    page.wait_for_selector('div[slot="credit-bar"]', timeout=5000)
                    page.set_viewport_size(ViewportSize(width=485, height=1080))
                    page.evaluate(f"""
                            () => {{
                                const creditBar = document.querySelector('div[slot="credit-bar"]');
                                const postTitle = document.querySelector('h1#post-title-t3_{id}');
                                const postFlair = document.querySelector('shreddit-post-flair[slot="post-flair"]');

                                if (!creditBar || !postTitle) return;

                                // Remove the <time> and <span> elements from the credit bar
                                const timeElement = creditBar.querySelector('time');
                                if (timeElement) {{
                                    timeElement.remove();
                                }}

                                const spanElement = creditBar.querySelector('span.flex.items-center.pl-xs');
                                if (spanElement) {{
                                    spanElement.remove();
                                }}

                                // Create a wrapper for both elements
                                const wrapper = document.createElement('div');
                                wrapper.id = 'screenshot-wrapper';
                                wrapper.style.position = 'absolute';
                                wrapper.style.padding = '20px';
                                wrapper.style.zIndex = '9999';
                                wrapper.style.border = '1px solid black';
                                wrapper.style.top = '0';
                                wrapper.style.left = '0';
                                wrapper.style.background = 'black';
                                wrapper.style.color='white';
                                                                
                                // Clone the creditBar element
                                const creditBarClone = creditBar.cloneNode(true);

                                // Append creditBar first
                                wrapper.appendChild(creditBarClone);
                                
                                if(document.querySelector('shreddit-post').shadowRoot.querySelector('shreddit-content-tags[nsfw]')){{
                                    const tag = document.createElement("shreddit-content-tags");
                                    tag.setAttribute("nsfw", "");
                                    tag.style.paddingLeft = '20px';
                                    wrapper.appendChild(tag);
                                }}

                                // Clone and append the postTitle
                                const postTitleClone = postTitle.cloneNode(true);
                                wrapper.appendChild(postTitleClone);

                                // If the postFlair element exists, append it below the post title
                                if (postFlair) {{
                                    const postFlairClone = postFlair.cloneNode(true);
                                    postFlairClone.style.paddingLeft = '18px';
                                    wrapper.appendChild(postFlairClone);
                                }}
                                
                                
                                // If the postContainer element exists, append it at the bottom
                                if(document.querySelector('shreddit-post').shadowRoot.querySelector('div.shreddit-post-container')){{
                                    const postContainer = document.querySelector('shreddit-post').shadowRoot.querySelector('div.shreddit-post-container');
                                    const postContainerClone = postContainer.cloneNode(true);
                                    wrapper.appendChild(postContainerClone);
                                }}

                                // Append the wrapper to the body
                                document.body.appendChild(wrapper);
                                wrapper.querySelectorAll("*").forEach(el => {{
                                    el.style.color = 'white';
                                }});
                            }}
                        """)
                    # Take screenshot of the wrapper
                    wrapper = page.query_selector("#screenshot-wrapper")
                    if wrapper:
                        wrapper.screenshot(path=postcontentpath)
                    else:
                        print("Wrapper not found or failed to inject.")
                else:
                    page.locator('shreddit-post').screenshot(path=postcontentpath)
                    # page.locator('[data-test-id="post-content"]').screenshot(path=postcontentpath)
            except TimeoutError as e:
                print(f'attempt: {attempt}, failed with error {e}')
                continue
            break

        if not settings.config['settings']['storymode']:
            for idx, comment in enumerate(
                track(reddit_object["comments"], "Downloading screenshots...")
            ):
                # Stop if we have reached the screenshot_num
                if idx >= screenshot_num:
                    break

                if page.locator('[data-testid="content-gate"]').is_visible():
                    page.locator('[data-testid="content-gate"] button').click()

                page.goto(f'https://reddit.com{comment["comment_url"]}', timeout=0)

                # translate code

                if settings.config["reddit"]["thread"]["post_lang"]:
                    comment_tl = ts.google(
                        comment["comment_body"],
                        to_language=settings.config["reddit"]["thread"]["post_lang"],
                    )
                    page.evaluate(
                        '([tl_content, tl_id]) => document.querySelector(`#t1_${tl_id} > div:nth-child(2) > div > div[data-testid="comment"] > div`).textContent = tl_content',
                        [comment_tl, comment["comment_id"]],
                    )
                try:
                    page.locator(f"#t1_{comment['comment_id']}").screenshot(
                        path=f"assets/temp/{id}/png/comment_{idx}.png"
                    )
                except TimeoutError:
                    del reddit_object["comments"]
                    screenshot_num += 1
                    print("TimeoutError: Skipping screenshot...")
                    continue
        browser.close()
        print_substep("Screenshots downloaded Successfully.", style="bold green")
