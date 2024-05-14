import re
import time
import random
import os.path
import selenium.webdriver
from openai import OpenAI
import undetected_chromedriver
from selenium.webdriver.common.by import By
import azure.cognitiveservices.speech as speechsdk
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as Ec
from selenium.common import NoSuchElementException, StaleElementReferenceException, TimeoutException


browser: selenium.webdriver.Chrome | None = None


def wait_for_element(driver: undetected_chromedriver.Chrome, timeout: float, selector_type: str, selector_text: str):
    return WebDriverWait(driver, timeout).until(Ec.element_to_be_clickable((selector_type, selector_text)))


class Speaker(object):
    def __init__(self, service, **kwargs):
        self.service = service
        if self.service == 'OpenAI':
            self.client = OpenAI(api_key=kwargs['open_ai_key'])
        else:
            self.key = kwargs['azure_key']
            self.region = kwargs['azure_region']

    def generate_speech(self, file, text):
        if self.service == 'OpenAI':
            voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
            voice = voices[random.randint(0, len(voices) - 1)]
            text_chunks = []
            while len(text) > 4096:
                last_full_stop_index = text.rfind('.', 0, 4096)
                if last_full_stop_index == -1:
                    last_full_stop_index = 4096
                text_chunks.append(text[:last_full_stop_index + 1])
                text = text[last_full_stop_index + 1:].strip()
            text_chunks.append(text)
            audio = bytes()
            for chunk in text_chunks:
                response = self.client.audio.speech.create(model="tts-1", voice=voice, input=chunk)
                for byte in response.iter_bytes():
                    audio = audio + byte
            with open(file=file, mode='wb') as file:
                file.write(audio)
        else:
            voices = [
                'en-AU-NatashaNeural',
                'en-AU-WilliamNeural',
                'en-AU-AnnetteNeural',
                'en-AU-CarlyNeural',
                'en-AU-DarrenNeural',
                'en-AU-DuncanNeural',
                'en-AU-ElsieNeural',
                'en-AU-FreyaNeural',
                'en-AU-JoanneNeural',
                'en-AU-KenNeural',
                'en-AU-KimNeural',
                'en-AU-NeilNeural',
                'en-AU-TimNeural',
                'en-AU-TinaNeural',
                'en-CA-ClaraNeural',
                'en-CA-LiamNeural',
                'en-GB-SoniaNeural',
                'en-GB-RyanNeural',
                'en-GB-LibbyNeural',
                'en-GB-AbbiNeural',
                'en-GB-AlfieNeural',
                'en-GB-BellaNeural',
                'en-GB-ElliotNeural',
                'en-GB-EthanNeural',
                'en-GB-HollieNeural',
                'en-GB-NoahNeural',
                'en-GB-OliverNeural',
                'en-GB-OliviaNeural',
                'en-GB-ThomasNeural',
                'en-IE-EmilyNeural',
                'en-IE-ConnorNeural',
                'en-US-JennyMultilingualNeural',
                'en-US-JennyNeural',
                'en-US-GuyNeural',
                'en-US-AriaNeural',
                'en-US-DavisNeural',
                'en-US-AmberNeural',
                'en-US-AndrewNeural',
                'en-US-AshleyNeural',
                'en-US-BrandonNeural',
                'en-US-BrianNeural',
                'en-US-ChristopherNeural',
                'en-US-CoraNeural',
                'en-US-ElizabethNeural',
                'en-US-EmmaNeural',
                'en-US-EricNeural',
                'en-US-JacobNeural',
                'en-US-JaneNeural',
                'en-US-JasonNeural',
                'en-US-MichelleNeural',
                'en-US-MonicaNeural',
                'en-US-NancyNeural',
                'en-US-RogerNeural',
                'en-US-SaraNeural',
                'en-US-SteffanNeural',
                'en-US-TonyNeural',
                'en-ZA-LeahNeural',
                'en-ZA-LukeNeural'
            ]
            voice = voices[random.randint(0, len(voices)-1)]
            speech_config = speechsdk.speech.SpeechConfig(subscription=self.key, region=self.region)
            speech_config.speech_synthesis_voice_name = voice
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = speech_synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                stream = speechsdk.AudioDataStream(result)
                stream.save_to_wav_file(file)
            else:
                print(f"Speech synthesis failed. Reason: {result.reason}, Details: {result.cancellation_details.error_details}")


def safe_filename(text: str):
    text = os.path.normpath(text)
    dirname = os.path.dirname(text)
    filename, extension = os.path.splitext(os.path.basename(text))
    filename = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "_", filename).rstrip('._ ')
    return os.path.join(dirname, filename + extension)


def get_tag_type(tag: str):
    pattern = r'<\s*([a-zA-Z0-9_-]+)[^>]*\/?>|<\/\s*([a-zA-Z0-9_-]+)\s*>'
    matches = re.findall(pattern, tag)
    if matches: return matches[0][0] if matches[0][0] else matches[0][1]
    else:
        if re.search(r'<!--.+-->', tag):
            return None
        else:
            raise Exception(f'Did not find a html tag in \'{tag}\'.')


def parse_trees(html: str) -> list[list[str]]:
    trees = []
    ordered_html = []
    current_text = ""
    current_tag = ""
    parsing_tag = False
    open_tags = []
    for character in html:
        if parsing_tag:
            current_tag += character
            if character == '>':
                if current_text:
                    ordered_html.append(current_text)
                    current_text = ""
                ordered_html.append(current_tag)
                if current_tag.endswith('/>'):
                    if not open_tags:
                        trees.append(ordered_html)
                        ordered_html = []
                elif current_tag.startswith('</'):
                    if open_tags:
                        if open_tags[-1].startswith(f'<{get_tag_type(current_tag)}'):
                            open_tags = open_tags[:-1]
                        else:
                            count = 0
                            while get_tag_type(open_tags[-1]) in ['img', 'a', 'br', 'hr']:
                                count += 1
                                open_tags = open_tags[:-1]
                                if open_tags[-1].startswith(f'<{get_tag_type(current_tag)}'):
                                    open_tags = open_tags[:-1]
                                    break
                                if count > 100:
                                    raise Exception(f'Expected to close the last open tag {open_tags[-1]}, but {current_tag} does not close it.')
                    if not open_tags:
                        trees.append(ordered_html)
                        ordered_html = []
                else:
                    if current_tag != '<br>':
                        open_tags.append(current_tag)
                current_tag = ""
                parsing_tag = False
        elif character == '<':
            current_tag += character
            parsing_tag = True
        else:
            current_text += character
    if ordered_html:
        trees.append(ordered_html)
    return trees


def convert_trees_to_dicts(trees, split_on_trees=True, try_split_after=0, split_on_opening_tags_callback=None):
    def create_card():
        nonlocal card_text, card_html, text_length
        open_tags = []
        for tag in card_html:
            if '<' not in tag or '/>' in tag:
                continue
            if '</' in tag:
                if get_tag_type(open_tags[-1]) == get_tag_type(tag):
                    open_tags = open_tags[:-1]
                else:
                    count = 0
                    while get_tag_type(open_tags[-1]) in ['br', 'hr', 'img', 'a']:
                        count += 1
                        open_tags = open_tags[:-1]
                        if open_tags[-1].startswith(f'<{get_tag_type(tag)}'):
                            open_tags = open_tags[:-1]
                            break
                        if count > 100:
                            raise Exception(f'Expected to close the last open tag {open_tags[-1]}, but {tag} does not close it.')
            else:
                open_tags.append(tag)
        card_html.extend([f'</{get_tag_type(tag)}>' for tag in reversed(open_tags) if get_tag_type(tag) not in ['br']])
        while get_tag_type(card_html[0]) == 'br' or card_html[0] in [" "]: del card_html[0]
        while get_tag_type(card_html[-1]) == 'br' or card_html[-1] in [" "]: del card_html[-1]
        for tag in reversed(card_html):
            if '<' not in tag: break
            if get_tag_type(tag) == 'br': card_html.remove(tag)
        for tag in card_html:
            if '<' not in tag: break
            if get_tag_type(tag) == 'br': card_html.remove(tag)

        flashcards.append({'text': re.sub(r'\n+', '\n', re.sub(r' +', ' ', ' '.join(card_text).strip().replace('&nbsp;', ' ').replace('\xa0', '').replace(' \n ', '\n'))), 'html': ''.join(card_html)})
        card_text, card_html, text_length = [], open_tags, 0

    flashcards, card_text, card_html, text_length = [], [], [], 0
    for tree in trees:
        if len(tree) > 1 and split_on_trees:
            if try_split_after and text_length < try_split_after:
                pass
            else:
                create_card()
        for piece in tree:
            if piece.startswith('<'):
                if get_tag_type(piece) == 'br':
                    card_text += '\n'
                if try_split_after and text_length > try_split_after:
                    if (piece.startswith('<h1') or piece.startswith('<h2') or piece.startswith('<h3') or (split_on_opening_tags_callback is not None and split_on_opening_tags_callback(piece))) and "/" not in piece:
                        create_card()
            else:
                text_length += len(piece.split(' '))
                card_text.append(piece)
            card_html.append(piece)
        if card_text:
            card_text += '\n'

    if card_html:
        create_card()

    if len(flashcards) > 1 and len(flashcards[-1]['text'].split(' ')) < 250:
        flashcard = flashcards.pop(-1)
        flashcards[-1]['text'] += flashcard['text']
        flashcards[-1]['html'] += flashcard['html']
    return flashcards


def add_br_around_img_tags(html, add_before=True, add_after=True):
    if add_before:
        pattern = re.compile(f'(</?br/?>)?(</?img(?![^>]*</?img)[^>]*>)', re.IGNORECASE)
        html = pattern.sub(lambda match: '<br/>' + match.group(2) if match.group(1) is None else match.group(0), html)
    if add_after:
        pattern_after = re.compile(f'(</?img[^>]*>)(?!(?:</?br/?>))', re.IGNORECASE)
        html = pattern_after.sub(r'\1<br/>', html)
    return html


def scrape_trailhead(url, output_dir, audio_dir, speaker: Speaker, split_after=500, credentials=None, redo_successes=False):
    global browser

    def login_trailhead():
        global browser
        wait_for_element(browser, 30, By.CSS_SELECTOR, '#onetrust-reject-all-handler').click()
        shadow_root = browser.execute_script('return arguments[0].shadowRoot', wait_for_element(browser, 30, By.CSS_SELECTOR, '#contextnav'))
        shadow_root = browser.execute_script('return arguments[0].shadowRoot', shadow_root.find_element(By.CSS_SELECTOR, 'div.contextnav__ctas-button-container.cta-primary > hgf-button'))
        original_window_handle = browser.current_window_handle
        browser.execute_script("arguments[0].click();", shadow_root.find_element(By.CSS_SELECTOR, 'a'))
        new_tab_handle = None
        for window_handle in browser.window_handles:
            if window_handle != original_window_handle:
                new_tab_handle = window_handle
                break
        browser.close()
        browser.switch_to.window(new_tab_handle)
        time.sleep(2)
        shadow_root = browser.execute_script('return arguments[0].shadowRoot', wait_for_element(browser, 30, By.CSS_SELECTOR, "idx-standard-login-page"))
        shadow_root = browser.execute_script('return arguments[0].shadowRoot', shadow_root.find_element(By.CSS_SELECTOR, 'lwc-idx-user-login'))
        wait_for_element(shadow_root, 30, By.CSS_SELECTOR, 'button.idp-button.idp-button--google').click()
        wait_for_element(browser, 30, By.CSS_SELECTOR, '#identifierId').send_keys(credentials['username'])
        browser.find_element(By.CSS_SELECTOR, '#identifierNext').click()
        wait_for_element(browser, 30, By.CSS_SELECTOR, 'input[type=password]').send_keys(credentials['password'])
        browser.find_element(By.CSS_SELECTOR, '#passwordNext').click()
        wait_for_element(browser, 30, By.CSS_SELECTOR, 'thtoday-page')

    def scrape_trail_links():
        trail_title = None
        if 'trailmixes' in browser.current_url:
            shadow_root = browser.execute_script('return arguments[0].shadowRoot', wait_for_element(browser, 30, By.CSS_SELECTOR, 'tds-content-header'))
            shadow_root = browser.execute_script('return arguments[0].shadowRoot', shadow_root.find_element(By.CSS_SELECTOR, 'lwc-tds-content-summary'))
            shadow_root = browser.execute_script('return arguments[0].shadowRoot', shadow_root.find_element(By.CSS_SELECTOR, 'lwc-tds-summary'))
            trail_title = shadow_root.find_element(By.CSS_SELECTOR, 'div.body > div.content > lwc-tds-heading').text.strip()
        else:
            trail_title = browser.find_element(By.CSS_SELECTOR, 'h1').text.strip()

        content_dicts = []
        modules_elements = browser.find_elements(By.CSS_SELECTOR, 'div.tds-content-panel_body')
        _ = 0
        while _ < len(modules_elements):
            element = modules_elements[_]
            _ += 1
            content_text = element.find_element(By.CSS_SELECTOR, 'div:nth-child(2) > div:nth-child(2) > div').text.strip()
            try:
                element.find_element(By.CSS_SELECTOR, 'button').click()
                time.sleep(1)
            except NoSuchElementException:
                pass
            if not redo_successes:
                try:
                    element.find_element(By.CSS_SELECTOR, '.tds-bg_success')
                    if content_text in ['Module', 'Project', 'Superbadge', 'Trail']:
                        continue
                except NoSuchElementException:
                    pass
            title_element = element.find_element(By.CSS_SELECTOR, 'h2')
            title_text = title_element.text.strip()
            link_text = None
            try:
                link_text = title_element.find_element(By.CSS_SELECTOR, 'a').get_property("href")
            except NoSuchElementException:
                pass
            if content_text in ['Module', 'Project', 'Superbadge', 'Trail']:
                content_dicts.append({'type': content_text, 'trail_title': trail_title, 'module_title': title_text, 'link': link_text})
            elif content_text in ['Task', 'Link']:
                if link_text is None:
                    exam_weight = element.find_element(By.CSS_SELECTOR, 'div > div > p').text.strip()
                    content_dicts.append({'type': 'Exam Weight', 'trail_title': trail_title, 'module_title': title_text, 'link': exam_weight})
                elif link_text.startswith('https://help.salesforce.com/articleView') or link_text.startswith('https://help.salesforce.com/s/article'):
                    content_dicts.append({'type': 'Article', 'trail_title': trail_title, 'module_title': title_text, 'link': link_text})
                elif link_text.startswith('https://www.youtube.com/'):
                    content_dicts.append({'type': 'YouTube', 'trail_title': trail_title, 'module_title': title_text, 'link': link_text})
                elif link_text.startswith('https://trailhead.salesforce.com/en/academy/classes/') or link_text.startswith('https://trailhead.salesforce.com/credentials') or (link_text.startswith('https://trailhead.salesforce.com/help?article=') and link_text.endswith('Test')):
                    continue
                else:
                    content_dicts.append({'type': 'Other', 'trail_title': trail_title, 'module_title': title_text, 'link': link_text})
                    print(f'Unknown content type found at index: {str(_ + 1)}.')
        return content_dicts

    def create_flashcard_dicts(trail_title, module_title, unit_title, page_contents):
        html = ''
        for element in page_contents:
            html += re.sub(r'\s\s+', '', element.get_attribute('outerHTML').replace('\n', ''))

        # this removes the navbar when scraping articles
        html = re.sub(r'<nav.+</nav>', '', html)
        # This removes a warning about screen readers struggling to parse the page content
        html = re.sub(r'<div class="box message info"><div class="inner"><div class="bd"><div class="media"><img class="img mtm" role="presentation" src="https://res\.cloudinary\.com/hy4kyit2a/image/upload/doc/trailhead/en-usb473bb5ea1b7e61dfb07e6a7e547de6b\.gif" alt="Note"><div class="mediaBd"><div class="message-media-content"><h2 id="accessibility"><span>Accessibility</span></h2><p>This \S+ requires some additional instructions for screen reader users\. To access a detailed screen reader version of this \S+, click the link below:</p><p><a href="\S+" rel="noreferrer noopener" target="_blank">Open Trailhead screen reader instructions</a>\.</p></div></div></div></div></div></div>', '', html)
        # These 3 removes the 'Follow along with an instructor/expert title, paragraph and video element
        html = re.sub(r'<h2 id="follow-along-with-trail-together"><span>Follow Along with Trail Together</span></h2><p>Want to follow along with an \S+ as you work through this step\? Take a look at this video.+</p>(<p>|)<span><iframe width="\S+" height="\S+" src="\S+" allowfullscreen="" title="Video Content"></iframe></span>(<a id="hidden-content" href="#"></a>|)(</p>|)', '', html)
        html = re.sub(r'<p>\(This clip starts at .+, in case you want to rewind and watch the beginning of the step again\.\)</p>', '', html)
        html = re.sub(r'<h2 id="related-badges"><span>Related Badges</span></h2><p>Looking for more information\? Explore these related badges.+</p><table.+</tbody></table>', '', html)
        # Remove the screen reader warning
        html = re.sub(r'<h2 id="accessibility"><span>Accessibility</span></h2>This unit requires some additional instructions for screen reader users\. To access a detailed screen reader version of this unit, click the link below\.<br><br><a href="https://developer\.salesforce\.com/files/accessibility/session_based_perms/session_based_access/index\.html" target="_blank" rel="noreferrer noopener"><u>Open Trailhead screen reader instructions</u></a>', '', html)


        html = add_br_around_img_tags(html, add_before=True, add_after=True)
        trees = parse_trees(html)
        flashcards = convert_trees_to_dicts(trees, split_on_trees=False, try_split_after=split_after)
        for index, flashcard in enumerate(flashcards, start=1):
            flashcard['trail_title'] = trail_title
            flashcard['module_title'] = module_title
            flashcard['unit_title'] = unit_title
            flashcard['card_index'] = str(index)

        try:
            browser.find_element(By.CSS_SELECTOR, '#challenge')
            flashcards[-1]['html'] += f'<a href="{browser.current_url}#challenge">Complete the Challenge!</a>'
        except NoSuchElementException:
            pass
        return flashcards

    def write_flashcards(flashcards, speaker: Speaker):
        name = flashcards[0]["trail_title"] if flashcards[0]["trail_title"] else flashcards[0]["module_title"] if flashcards[0]["module_title"] else flashcards[0]["unit_title"]
        with open(file=f'{output_dir}{name}.csv', mode='w', encoding='utf-8') as file:
            for index, flashcard in enumerate(flashcards, start=1):
                print(f'Writing cards: {index} of {len(flashcards)}')
                audio = False
                filepath = f'{safe_filename(flashcard["unit_title"] + '_' + flashcard["card_index"])}.wav'
                if speaker is not None:
                    if os.path.isfile(f'{audio_dir}{filepath}'):
                        audio = True
                    else:
                        try:
                            speaker.generate_speech(f'{audio_dir}{filepath}', flashcard['text'])
                            audio = True
                        except Exception as e:
                            print(f'Audio generation failed for {filepath}! You will need to rerun the script to retry it (existing audio files will not be recreated).', e)
                            if os.path.isfile(f'{audio_dir}{filepath}'):
                                os.remove(f'{audio_dir}{filepath}')
                file.write(
                    f'{flashcard["trail_title"] + ' > ' if flashcard["trail_title"] else ''}{flashcard["module_title"] + ' > ' if flashcard["module_title"] else ''}{flashcard["unit_title"]}: {flashcard["card_index"]}\t' +
                    f'{flashcard["html"]}\t' +
                    (f'<audio controls=""><source src="{filepath}" type="audio/wav"></audio>' if audio else '') + '\t' +
                    (f'[sound:{filepath}]' if audio else '') + '\t' +
                    f'Incremental_Learning::Salesforce::{'Trail::' + flashcard["trail_title"].replace(' ', '_') + '::' if flashcard["trail_title"] else ''}{('Module::' + (flashcard["module_index"] + '_' if flashcard["module_index"] else '') + (flashcard["module_title"].replace(' ', '_') + '::' if flashcard["module_title"] else '') if flashcard["module_title"] else "")}{('Unit::' + (flashcard["unit_index"] + '_' if flashcard["unit_index"] else '') + (flashcard["unit_title"].replace(' ', '_') if flashcard["unit_title"] else '')) if flashcard["unit_title"] else ""}{'::' + flashcard["card_index"] if flashcard["card_index"] else ''}\n'
                )

    if browser is None:
        browser = undetected_chromedriver.Chrome()
        browser.maximize_window()
        browser.get('https://trailhead.salesforce.com/')
        if credentials is not None:
            login_trailhead()
        else:
            input('Please log in, then press the enter key in the terminal!')
    browser.get(url)
    wait_for_element(browser, 30, By.CSS_SELECTOR, '#main-wrapper')
    activities = []
    if 'trailmixes' in browser.current_url:
        activities = scrape_trail_links()
    elif browser.current_url.startswith('https://trailhead.salesforce.com/content/learn/trails/'):
        activities = scrape_trail_links()
    elif browser.current_url.startswith('https://trailhead.salesforce.com/content/learn/modules/') or browser.current_url.startswith('https://trailhead.salesforce.com/content/learn/projects/'):
        module_title = wait_for_element(browser, 30, By.CSS_SELECTOR, 'h1').text.strip()
        units = browser.find_elements(By.CSS_SELECTOR, '.tds-content-panel__unit')
        if units: activities.append({'type': 'Module', 'module_title': module_title, 'link': url})
        else: activities.append({'type': 'Unit', 'link': url})
    # TODO: Add support for scraping article and dev documentation as solo input, solo units and modules may not be working properly yet

    flashcards = []
    for module_order, content_dicts in enumerate(activities, start=1):
        completed = False
        while not completed:
            try:
                print(f'Scraping content: {module_order} of {len(activities)}')
                content_dicts.setdefault("trail_title", "")
                content_dicts.setdefault("module_index", "")
                content_dicts.setdefault("module_title", "")
                content_dicts.setdefault("unit_index", "")
                content_dicts.setdefault("unit_title", "")
                content_dicts.setdefault("card_index", "")
                if content_dicts['type'] == 'Exam Weight':
                    flashcard = {'trail_title': content_dicts["trail_title"], 'module_index': str(module_order), 'module_title': content_dicts["module_title"], 'unit_index': "1", 'unit_title': 'Exam Weight', 'card_index': "1", 'text': f'{content_dicts["module_title"]}: {content_dicts["link"]}', 'html': content_dicts['link']}
                    flashcards.append(flashcard)
                elif content_dicts['type'] == 'Article':
                    browser.get(content_dicts['link'])
                    try:
                        wait_for_element(browser, 30, By.CSS_SELECTOR, 'html')
                        body = wait_for_element(browser, 30, By.CSS_SELECTOR, 'body')
                        shadow_root = browser.execute_script('return arguments[0].shadowRoot', wait_for_element(body, 30, By.CSS_SELECTOR, 'c-hc-article-viewer'))
                        shadow_root = wait_for_element(shadow_root, 30, By.CSS_SELECTOR, 'div')
                        shadow_root = browser.execute_script('return arguments[0].shadowRoot', wait_for_element(shadow_root, 30, By.CSS_SELECTOR, 'c-hc-documentation-article'))
                        content = shadow_root.find_element(By.CSS_SELECTOR, 'div > div > content > div > div')
                        units_elements = content.find_elements(By.XPATH, '*')
                        for flashcard in create_flashcard_dicts(content_dicts["trail_title"], content_dicts["module_title"], 'Article', units_elements):
                            flashcard["module_index"] = str(module_order)
                            flashcard["unit_index"] = "1"
                            flashcards.append(flashcard)
                    except (StaleElementReferenceException, TimeoutException):
                        if browser.current_url.startswith('https://developer.salesforce.com/docs/'):
                            flashcard = {'trail_title': content_dicts["trail_title"], 'module_title': content_dicts["module_title"], 'unit_title': 'Docs', 'text': 'Please review the following documentation.', 'html': f'<a href="{content_dicts['link']}">Go to Docs!</a>', "module_index": str(module_order), "unit_index": "1", "card_index": "1"}
                            flashcards.append(flashcard)
                        elif browser.current_url.startswith('https://help.salesforce.com/s/articleView'):
                            flashcard = {'trail_title': content_dicts["trail_title"], 'module_title': content_dicts["module_title"], 'unit_title': 'Article', 'text': 'Please review the following article.', 'html': f'<a href="{content_dicts['link']}">Go to Article!</a>', "module_index": str(module_order), "unit_index": "1", "card_index": "1"}
                            flashcards.append(flashcard)
                        else:
                            raise Exception('Could not recover from error when parsing Article.')
                elif content_dicts['type'] == 'Superbadge':
                    flashcard = {'trail_title': content_dicts["trail_title"], 'module_title': content_dicts["module_title"], 'unit_title': 'Exam Weight', 'text': f'Please complete the superbadge!', 'html': f'<a href="{content_dicts['link']}">Go to Superbadge!</a>'}
                    flashcard["module_index"] = str(module_order)
                    flashcard["unit_index"] = "1"
                    flashcard["card_index"] = "1"
                    flashcards.append(flashcard)
                elif content_dicts['type'] == 'Trail':
                    flashcards.extend(scrape_trailhead(content_dicts['link'], False, False, redo_successes))
                elif content_dicts['type'] in ['Module', 'Project']:
                    browser.get(content_dicts['link'])
                    unit_links = []
                    units_elements = browser.find_elements(By.CSS_SELECTOR, 'a.tds-content-panel__unit-link')
                    for element in units_elements:
                        unit_links.append(f'{element.get_property("href")}')
                    for unit_order, unit in enumerate(unit_links, start=1):
                        browser.get(unit)
                        unit_title = wait_for_element(browser, 30, By.CSS_SELECTOR, 'article > h1').text.strip()
                        unit_contents = browser.find_elements(By.CSS_SELECTOR, 'article > .unit-content > *')
                        for flashcard in create_flashcard_dicts(content_dicts["trail_title"], content_dicts["module_title"], unit_title, unit_contents):
                            flashcard["module_index"] = str(module_order)
                            flashcard["unit_index"] = str(unit_order)
                            flashcards.append(flashcard)
                elif content_dicts['type'] in ['Unit']:
                    navs = browser.find_elements(By.CSS_SELECTOR, 'nav > ol > li')
                    trail_title, module_title = '', ''
                    if navs:
                        if len(navs) == 3:
                            trail_title = navs[0].find_element(By.CSS_SELECTOR, 'a').text.strip()
                            module_title = navs[1].find_element(By.CSS_SELECTOR, 'a').text.strip()
                        elif len(navs) == 2:
                            module_title = navs[0].find_element(By.CSS_SELECTOR, 'a').text.strip()
                    unit_title = wait_for_element(browser, 30, By.CSS_SELECTOR, 'article > h1').text.strip()
                    unit_contents = browser.find_elements(By.CSS_SELECTOR, 'article > .unit-content > *')
                    for flashcard in create_flashcard_dicts(trail_title, module_title, unit_title, unit_contents):
                        flashcard["module_index"] = str(module_order)
                        flashcard["unit_index"] = str(1)
                        flashcards.append(flashcard)
                    pass
                elif content_dicts['type'] == 'YouTube':
                    flashcard = {'trail_title': content_dicts["trail_title"], 'module_title': content_dicts["module_title"], 'unit_title': 'YouTube', 'text': 'Please watch the following video.', 'html': f'<a href="{content_dicts['link']}">Watch the Video!</a>', "module_index": str(module_order), "unit_index": "1", "card_index": "1"}
                    flashcards.append(flashcard)
                else:
                    flashcard = {'trail_title': content_dicts["trail_title"], 'module_title': content_dicts["module_title"], 'unit_title': 'Other', 'text': 'Please review the following content.', 'html': f'<a href="{content_dicts['link']}">Go to Content!</a>', "module_index": str(module_order), "unit_index": "1", "card_index": "1"}
                    flashcards.append(flashcard)
                completed = True
            except Exception as e:
                print(e)
                pass

    write_flashcards(flashcards, speaker)

    return flashcards


def run(
    url='',
    csv_output_dir='.',
    audio_output_dir=r'.',
    redo_completed=False,
    split_after_x_chars=500,
    generate_tts=True,
    tts_service='OpenAI',
    open_ai_key='',
    azure_key='',
    azure_region='',
    log_into_google=False,
    google_username='',
    google_password=''
):
    speaker = None
    if generate_tts and tts_service in ['OpenAI','Azure']:
        speaker = Speaker(tts_service, open_ai_key=open_ai_key, azure_key=azure_key, azure_region=azure_region)
    if not csv_output_dir.endswith('/'):
        csv_output_dir += '/'
    if not audio_output_dir.endswith('/'):
        audio_output_dir += '/'
    flashcards = scrape_trailhead(url, csv_output_dir, audio_output_dir, speaker, split_after_x_chars, {'username': google_username, 'password': google_password} if log_into_google else None, redo_completed)
    for count, flashcard in enumerate(flashcards, start=1):
        print(f'{str(count)}: {str(flashcard)}')
