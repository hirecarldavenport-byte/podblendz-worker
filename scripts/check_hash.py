import hashlib

url = "https://prfx.byspotify.com/e/play.podtrac.com/npr-510312/npr.simplecastaudio.com/acf40eb5-ab43-4086-ae17-f1ef04b15913/episodes/f050fe0a-fed5-42d5-88d5-60cc6e2fadb5/audio/128/default.mp3?awCollectionId=acf40eb5-ab43-4086-ae17-f1ef04b15913&amp;awEpisodeId=f050fe0a-fed5-42d5-88d5-60cc6e2fadb5&amp;feed=KTjArdE7&amp;t=podcast&amp;e=nx-s1-5733992&amp;p=510312&amp;d=2176&amp;size=34824865"

print(hashlib.md5(url.encode()).hexdigest())