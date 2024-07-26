import re
import os
import json
import requests
import ffmpeg
from bs4 import BeautifulSoup as bs4
import urllib.request

def extract_js_var(soup, js_var):return json.loads(re.search('(?:var ' + js_var + ' = )({.*?})(?:;)', soup.find('script', text=re.compile(js_var, re.DOTALL)).string).group(1))

def custom_urldecode(encoded_text):
    index = 0
    decoded_text = ''

    while index < len(encoded_text):
        if encoded_text[index] == '%':
            hex_chars = encoded_text[index + 1:index + 3]
            try:
                decoded_char = bytes.fromhex(hex_chars).decode('utf-8')
                decoded_text += decoded_char
                index += 3
            except ValueError:
                decoded_text += encoded_text[index]
                index += 1
        else:
            decoded_text += encoded_text[index]
            index += 1

    return decoded_text

def get(link: str):
    data = requests.get(link).text
    soup = bs4(data, "html.parser")
    videos = extract_js_var(soup, "ytInitialPlayerResponse")["streamingData"]["adaptiveFormats"]
    js_url = re.search('"PLAYER_JS_URL":"/s/player/.+/base.js"', data).group(0).replace('PLAYER_JS_URL":"',"").replace('"',"")
    js = requests.get(f"https://youtube.com/{js_url}").text
    border = [k["mimeType"].split("/")[0] for k in videos].index("audio")
    audios = videos[border:]
    videos = videos[:border - 1]
    try:videos[0]["url"]
    except:
        drm = True
        videos = [{"itag": k["itag"], "signatureCipher": k["signatureCipher"], "mimeType": k["mimeType"], "fps": k["fps"], "qualityLabel": k["qualityLabel"]} for k in videos]
        audios = [{"itag": k["itag"], "signatureCipher": k["signatureCipher"], "mimeType": k["mimeType"], "averageBitrate": k["averageBitrate"], "audioQuality": k["audioQuality"]} for k in audios]
    else:
        drm = False
        videos = [{"itag": k["itag"], "url": k["url"], "mimeType": k["mimeType"], "fps": k["fps"], "qualityLabel": k["qualityLabel"]} for k in videos]
        audios = [{"itag": k["itag"], "url": k["url"], "mimeType": k["mimeType"], "averageBitrate": k["averageBitrate"], "audioQuality": k["audioQuality"]} for k in audios]
    return drm, videos, audios, js

def url_decode(chiper: str, js):
    audio_info = {}
    for info in chiper.split("&"):audio_info[info.split("=")[0]] = custom_urldecode(info.split("=")[1])
    decompile_pattern = re.search(r'a\s*=\s*a\.split\(""\);(.*?)return\s*a\.join\(""\)', js).group(0)
    func = [re.search('\{.+\}', k).group(0) for k in [re.search(k.split(".")[1].split("(")[0] + '\:function(.*?)\}', js).group(0) for k in decompile_pattern.split(";")[1:-1]]]
    s = list(custom_urldecode(audio_info["s"]))
    for k, data in zip(func, decompile_pattern.split(";")[1:-1]):
        if k == "{a.reverse()}":s.reverse()
        elif k == "{var c=a[0];a[0]=a[b%a.length];a[b%a.length]=c}":
            c = s[0]
            s[0] = s[int(data.split(",")[1].replace(")", "")) % len(s)]
            s[int(data.split(",")[1].replace(")", "")) % len(s)] = c
        elif k == "{a.splice(0,b)}":
            for k in range(int(data.split(",")[1].replace(")", ""))):s.pop(0)
    return audio_info["url"] + f"&sig={''.join(s)}"


if __name__ == "__main__":
    url = input("ダウンロードする動画のURLを入力してください")
    drm, videos, audios, js = get(url)
    video = videos[0]
    if drm:video["url"] = url_decode(video["signatureCipher"], js)
    audio = audios[-1]
    if drm:audio["url"] = url_decode(audio["signatureCipher"], js)
    ffmpeg.output(ffmpeg.input(video["url"]), f'input.mp4').run()
    ffmpeg.output(ffmpeg.input(audio["url"]), f'input.webm').run()
    stream = ffmpeg.output(ffmpeg.input("input.mp4"), ffmpeg.input("input.webm"), f'{bs4(requests.get(url).text).find("title").text.split(" - ")[0]}.mp4')
    stream.run()
    os.remove('input.mp4')
    os.remove("input.webm")
