import requests
from bs4 import BeautifulSoup
import os

# So the site isn't forbidden
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

base_url_char = "https://thewanderinginn.fandom.com/wiki/Category:Characters?from="

# List to hold the generated URLs
urls_char = []

# Generate URLs for letters A to Z to grab category data from the fandom
for letter in range(ord('A'), ord('Z') + 1):
    url_char = base_url_char + chr(letter)
    urls_char.append(url_char)


# to scrape all character pages urls from the categories page. Listed alphabetically
def scrape_characters(url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    char_data = []
    for paragraph in soup.find('ul', class_='category-page__members-for-char').find_all('a'):
        char_data.append(paragraph.get_text())
    return char_data


# Grab Characters to help in NER //will grab locations as well
characters = []
for url in urls_char:
    char_letter = url.split('=')[-1]
    print(f"Scraping {char_letter}...")
    temp_char = scrape_characters(url)
    characters.extend(temp_char)


# Gets rid of spaces that images cause in the list
clean_characters = []
for item in characters:
    if item != '\n\n\n':
        clean_characters.append(item)


#########################################################################################################
### Cleans the chapter data that comes through ###
def clean_text(text):
    lines = text.split('\n')
    # Make sure no spaces at start
    if(len(lines[0]) < 1):
        lines.pop(0)
        return clean_text('\n'.join(lines))
    # Gets rid of any header or introduction paragraph based on formatting and words in context. Recurses back in case of multiple
    if(lines[0][0] == '(' or (lines[0][0] == '[' and len(lines[0]) > 50)  or lines[0][0] == '<' or
       "https" in lines[0] or "Warning" in lines[0] or "editor" in lines[0]):
        lines.pop(0)
        lines.pop(0)
        return clean_text('\n'.join(lines))
    
    # Another header edge case, checks for text or links within a range a the start and recurses in case of extra text
    for i in range(min(15,len(lines))):
        if "pirateaba" in lines[i] or "https" in lines[0]:
            # Deletes until it hits an empty line to account for some cases.
            if(len(lines[i+1]) > 1):
                while len(lines[i+1]) > 1:
                    lines.pop(i+1)
            lines = lines[i+1:]
            return clean_text('\n'.join(lines))
    
    # Removes Author's note from the chapter
    sub = "Author’s Note:"
    if sub in text:
        
        #If Note is at end (No text will be after it)
        if(text.index(sub) > 1):
            text = text[0:text.index(sub)]
            return text
        #If Note is at beginning (It will end after a double line break) Also recurses as a check
        elif(text.index(sub) < 1):
            text = text[text.index('\xa0'):]
            return clean_text(text)
    
    #Removes next chapter/previous chapter text with chapters before Author's Note was used
    if len(lines) > 1:
        lines.pop()
        lines.pop()
    return '\n'.join(lines)

#########################################################################################################

# URL of the page containing chapter links
base_url = 'https://wanderinginn.com/table-of-contents/'

chapter_urls = []
# Send a request to the website
response = requests.get(base_url, headers=headers)
if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the container that holds the chapter links
    chapters_container = soup.find('article', class_='page page-toc')
    if chapters_container:
        # Find all links within the container
        for link in chapters_container.find_all('a'):
            if link.get('href') and (link.text.strip() and not link.get('class')):
                href = link.get('href')
                chapter_urls.append(href)
else:
    print(f"Failed to retrieve page: {response.status_code}")
    
# scrapes chapter links from table of contents page
def scrape_chapter(url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    text_data = ""
    for paragraph in soup.find('div', class_='entry-content').find_all('p'):
        text_data += paragraph.get_text() + "\n"
    # sends to clean the text
    cleaned_text = clean_text(text_data)
    return cleaned_text

# scrapes from each chapter url from above and stores in chapters
chapters = {}
for url in chapter_urls:
    chapter_number = url.split('/')[-2]
    print(f"Scraping {chapter_number}...")
    chapters[chapter_number] = scrape_chapter(url)
    

# Save chapters under a folder with each file separate
os.makedirs('ordered_chapters', exist_ok=True)

# Save each chapter with a sequential index so that it will be listed in order read
# Chapter numbers can be finicky so this provides a release order.
for i, (chapter_number, text) in enumerate(chapters.items(), start=1):
    filename = os.path.join('ordered_chapters', f"{i:04d}_Chapter_{chapter_number}.txt")
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(text)

print("Chapters saved in the order they were scraped.")

# Save chapters all in one text file
combined_text = "\n\n".join([f"{text}" for number, text in chapters.items()])

# Save combined text to a file
with open('all_chapters.txt', 'w', encoding='utf-8') as file:
    file.write(combined_text)