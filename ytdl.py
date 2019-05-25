from __future__ import unicode_literals
import youtube_dl
import googleapiclient.discovery
import json
import os, time

now = time.time()

# Looks at all items listed in the order file ./ytdl_order.json
# generated by '/scripts.php?script=ytdl', which is an array of
# { name, url, path }. Checks if the video is already downloaded.
# If not, `youtube-dl` utility downloads it. Comments will allways
# be (re)retrieved using the Google API. The video and metadata file
# are stored into the `path` folder, which is created if necessary.

with open("ytdl_order.json") as f:
	data = json.load(f)

with open('ytapikey.txt') as f:
	ytapikey = f.readline().strip()
ytapi = googleapiclient.discovery.build("youtube","v3",developerKey=ytapikey)

# Alternative storage location for video files; False to store the video file
#  alongside other files.
altstore = "/srv/stor/links"

update_comm_every_n_days = 7

i = 0
for item in data:
	i += 1

	print("--------------------------------------------------------------------")
	print(i,"/",len(data)," - ",item['path'])
	print()

	# Create directory if necessary
	path = "files"+item['path']
	if not os.path.exists(path):
		os.mkdir(path)

	# Download video if necessary
	if not os.path.exists(path+"/video.mp4"):
		url = "https://www.youtube.com/watch?v="+item['vid']
		print("Downloading @",url)
		ydl_opts = {
			'format': 'best[ext=mp4][height<=720]',
			'outtmpl': path+"/video.%(ext)s" if (altstore == False) else altstore+"/%(id)s.%(ext)s",
		}
		try:
			with youtube_dl.YoutubeDL(ydl_opts) as ydl:
				ydl.download([url])
			if altstore != False:
				os.symlink( altstore+"/"+item['vid']+".mp4", path+"/video.mp4" )
		except:
			print("Failed to download video !")

	# Retrieve metadata using Google API
	#  but only if last retrieval is less than 7 day old
	metadata_path = path+"/metadata.json"
	if not os.path.exists(metadata_path) or os.stat(metadata_path).st_mtime < now - update_comm_every_n_days*24*3600:

		# Get video metadata
		ytvid = ytapi.videos().list(
			part='snippet',
			id=item['vid'],
		).execute()
		print("Channel :",ytvid['items'][0]['snippet']['channelTitle'])
		print("Video title :",ytvid['items'][0]['snippet']['title'])
		print("Published at :",ytvid['items'][0]['snippet']['publishedAt'])

		# Get video comments
		comments = []
		try:
			ytcom = ytapi.commentThreads().list(
				part='snippet,replies',
				order='relevance',
				maxResults=50,
				videoId=item['vid'],
				textFormat='html'
			).execute()
			for comment in ytcom['items']:
				replies = []
				if comment['snippet']['totalReplyCount'] != 0 and 'replies' in comment:
					for reply in comment['replies']['comments']:
						replies.append({
							'author': reply['snippet']['authorDisplayName'],
							'date': reply['snippet']['publishedAt'],
							'html': reply['snippet']['textDisplay']
						})
				comments.append({
					'author': comment['snippet']['topLevelComment']['snippet']['authorDisplayName'],
					'date': comment['snippet']['topLevelComment']['snippet']['publishedAt'],
					'html': comment['snippet']['topLevelComment']['snippet']['textDisplay'],
					'replies': replies
				})
		except:
			print("Failed to retrieve comments")

		# Save video metadata & comments
		video_data = {
			'info': ytvid['items'][0]['snippet'],
			'comments': comments
		}
		with open(metadata_path, 'w') as f:
			json.dump(video_data, f, ensure_ascii=True)

	print()

os.remove("ytdl_order.json")
