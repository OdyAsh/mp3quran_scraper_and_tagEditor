from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import json
import pandas as pd
import os
import eyed3
import glob
from tqdm import tqdm

# Note: apparently there's no need for "global" keyword in functions, as the variables in the __main__ "if" statement are used in reading only not writing (in the functions) 

def save_file_at_dir(dir_path, filename, file_response, mode='wb'): # note: 'wb' not 'w' because we are storing audio not text. source 1: https://stackoverflow.com/questions/37573483/progress-bar-while-download-file-over-http-with-requests, source 2: https://from-locals.com/python-save-file-at-new-dir/
    os.makedirs(dir_path, exist_ok=True)
    total = int(file_response.headers.get('content-length', 0))

    with open(os.path.join(dir_path, filename), mode) as f, tqdm(
        desc = filename,
        total = total,
        unit = 'iB',
        unit_scale = True,
        unit_divisor = 1024,
    ) as bar:
        for mp3_content in file_response.iter_content(chunk_size=1024):
            size = f.write(mp3_content)
            bar.update(size)

def downloadAudio():
    for i in range(len(surahsDetails)):
        surahDic = json.loads(surahsDetails[i].attrs[':sora'])
        mp3FileName = str(surahDic['sora_num']) + " " + wikiSurahs[wikiSurahs['#'] == surahDic['sora_id']]['Anglicized title(s)']
        mp3FileName = mp3FileName.values[0] + ".mp3"
        if (os.path.exists(f'./{folderName}/{mp3FileName}')):
            continue
        mp3Link = surahDic['sora_audio']
        try:
            mp3 = session.get(mp3Link, stream = True, verify = True) # "verify" argument could be set to False to help fix ConnectionError "attempt failed because the connected party did not properly respond after a period of time"
        except:
            continue
        save_file_at_dir(folderName, mp3FileName, mp3) # ".content" accesses the audio of the get request in case you use a link that downloads an mp3 file

def extractSentences(fullString):
    sentences = ['', '', ''] # 0: first English sentence, 1: Arabic sentence, 2: second English sentence
    idx = 0
    for char in fullString:
        try:
            ascii = ord(char) # returns ASCII, ex: ord('A') == 65
            if (ascii >= 0 and ascii <= ord('z')):
                if (ascii == ord(' ')):
                    sentences[idx] += char
                elif (idx == 1):
                    idx += 1
                    sentences[idx] += char
                else:
                    sentences[idx] += char
            else:
                raise
        except:
            idx += (idx == 0)
            sentences[idx] += char
    return sentences

def constructTranslation(df):
    fullTranslation = ""
    for index, row in df.iterrows():
        sentences = extractSentences(row[0])
        fullTranslation += f"{sentences[0]}\n{sentences[1]}\n{sentences[2]}\n\n\n"
    return fullTranslation

def addTranslationAndTafsirToFiles():
    for (i, file) in tqdm(enumerate(audioFiles)):
        f = eyed3.load(file)
        if ((len(f.tag.lyrics) != 0) and f.tag.lyrics[0].text.find("Tafsir:") != -1):
            continue
        surahPage = session.get(f"https://quran411.com/stacked-view?sn={i+1}")
        df = pd.read_html(surahPage.content)[0]
        translationAndTafsir = constructTranslation(df)

        soup = BeautifulSoup(surahPage.text, 'html.parser')
        tafsir = soup.findAll('div', class_ = "ac-content")[-1].text.strip()
        translationAndTafsir += f"Tafsir:\n\n\n{tafsir}"
        f.tag.lyrics.set(translationAndTafsir)
        f.tag.save()

if __name__ == "__main__":
    try:
        eyed3.log.setLevel("ERROR") # to supress warnings related to eyed3
        quranLink = input('Enter mp3quran.net reciter page \n(example: https://mp3quran.net/eng/ryan):\n')
        wikipediaLink = "https://en.wikipedia.org/wiki/List_of_chapters_in_the_Quran"
        folderName = input("\nEnter folder name to save Surahs in \n(folder will be created next to this exe file) \n(example: Quran Recitations):\n")
        print("\nDownloading audio...")
        
        surahsAudiosPage = requests.get(quranLink).text
        surahsAudiosSoup = BeautifulSoup(surahsAudiosPage, "html.parser") 
        surahsDetails = surahsAudiosSoup.select("card-sora")
        wikiSurahs = pd.read_pickle("./surahsFromWiki.pickle")
        
        session = requests.Session() # These 5 lines are to avoid ConnectionError "attempt failed because the connected party did not properly respond after a period of time"
        retry = Retry(connect=3, backoff_factor=0.5) # source: https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        downloadAudio()
        print("\nFinished!\n\nDownloading translation and tafsir...")

        audioFiles = glob.glob(folderName + "/*.mp3")
        addTranslationAndTafsirToFiles()
        print("\nFinished!!\n\nApplying cover arts...")

        quranImgs = glob.glob("QuranImages/*") # Source for images: https://www.thelastdialogue.org/quran-summary/
        for i, file in tqdm(enumerate(audioFiles)):
            f = eyed3.load(file)
            with open(quranImgs[i], "rb") as cover_art:
                f.tag.images.set(3, cover_art.read(), "image/jpeg")
            f.tag.save()
        print("\nFinished!!!\n\nChanging folder name to add reciter...")

        reciter = surahsAudiosSoup.find('h1').text
        reciter = reciter[0 : reciter.find(' - ')]
        os.rename(folderName, f"{folderName} ({reciter})")
        print("Finished!!!!\n\n")
    except:
        print("\nPoor internet connection...\nPlease try again (with same folder name to resume downloading)\n")
    finally:
        while True:
            key = input("Press 'q' to exit...")
            if (key == 'q'):
                break
            print()
    






