####################################################################################################
# CityLine
#
# This Plex Channel allows users to watch videos from the CityLine website.
#
####################################################################################################

import re

#Channel Constants
PREFIX   = '/video/cityline'
NAME     = 'CityLine'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'

VIDEO_PAGE = 'http://www.cityline.tv/video'
SECTIONS_URL = 'http://www.cityline.tv/wp-json/rdm-video-cloud/video/sections'

HTTP_HEADERS = {
    'User-Agent': 'ABC/5.0.3(iPad4,4; cpu iPhone OS 9_3_4 like mac os x; en-nl) CFNetwork/758.5.3 Darwin/15.6.0',
    'appversion': '5.0.0'
}

####################################################################################################
def Start():

    ObjectContainer.title1 = NAME
    ObjectContainer.art = R(ART)
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)
    VideoClipObject.thumb = R(ICON)
    VideoClipObject.art = R(ART)

    HTTP.CacheTime = CACHE_1HOUR

    #Grab the wp_nonce and ajax_nonce values from the website so the channel can make JSON calls for the videos
    #These two values change daily and are required as parameters to pass to the website to get data
    page = HTML.ElementFromURL(VIDEO_PAGE)
    cdata = page.xpath('//script[contains(.,"rdmVideo")]/text()')
    cdata = ''.join(cdata)

    ajax_nonce = re.search(r"_ajaxnonce\":\"\w+", cdata).group()
    ajax_nonce = ajax_nonce.replace('_ajaxnonce":"', '')

    wp_nonce = re.search(r"_wpnonce\":\"\w+", cdata).group()
    wp_nonce = wp_nonce.replace('_wpnonce":"', '')

    Dict['AJAX_NONCE'] = ajax_nonce
    Dict['WP_NONCE'] = wp_nonce

    Log('AJAX_NONCE: ' + ajax_nonce)
    Log('WP_NONCE: ' + wp_nonce)


####################################################################################################
@handler(PREFIX, NAME, thumb=ICON, art=ART)
def MainMenu():

    oc = ObjectContainer()

    #Grab section names from the JSON API
    try:
        json_obj = JSON.ObjectFromString(GetData(SECTIONS_URL))
    except:
        return ObjectContainer(header="Empty", message="Cannot grab categories from the RSS Feed")

    for section in json_obj:
        category_name = section['name'].replace('&amp;', '&')
        oc.add(DirectoryObject(key=Callback(LoadCategory, title=category_name, cat_id=section['id']), title=category_name))

    return oc

####################################################################################################
@route(PREFIX + '/category')
def LoadCategory(title, cat_id):

    AJAX_NONCE = Dict['AJAX_NONCE']
    WP_NONCE = Dict['WP_NONCE']
    PUB_ID = "2226196965001"

    #Example category JSON call:
    #http://www.cityline.ca/wp-json/rdm-video-cloud/video/section?_ajax_nonce=4b25545a16&_wpnonce=58c709b9e1&id=full-episodes&var=category&order=1
    section_url = "http://www.cityline.tv/wp-json/rdm-video-cloud/video/section?_ajax_nonce=%s&_wpnonce=%s&id=%s&var=category&order=1" % (AJAX_NONCE, WP_NONCE, cat_id)

    #Grab videos for the category just called
    try:
        json_obj = JSON.ObjectFromString(GetData(section_url))
    except:
        return ObjectContainer(header="Empty", message="Cannot connect to category RSS Feed")

    oc = ObjectContainer(title2=title)

    for video in json_obj['data']['posts']:
        video_url = "http://c.brightcove.com/services/mobile/streaming/index/master.m3u8?videoId=%s&pubId=%s" % (video['bcid'], PUB_ID)
        title = video['title']
        date = video['date']['display']
        date = Datetime.ParseDate(date)
        summary = video['raw_excerpt']
        thumb = video['thumbnail']['src']
        duration = ToSeconds(video['duration']) * 1000

        oc.add(
            CreateVideoClipObject(
                video_url=video_url,
                title=title,
                summary=summary,
                duration=duration,
                thumb=thumb
            )
        )

    return oc

####################################################################################################
@route(PREFIX + '/createvideoclipobject', duration=int, include_container=bool)
def CreateVideoClipObject(video_url, title, summary, duration, thumb, include_container=False, **kwargs):

    videoclip_obj = VideoClipObject(
            key = Callback(CreateVideoClipObject, video_url=video_url, title=title, summary=summary, duration=duration, thumb=thumb, include_container=True),
            rating_key = video_url,
            title = title,
            summary = summary,
            duration = duration,
            thumb = thumb,
            items = [
                MediaObject(
                    parts = [
                        PartObject(key=Callback(PlayVideo, url=video_url))
                    ],
                    container = Container.MP4,
                    video_codec = VideoCodec.H264,
                    audio_codec = AudioCodec.AAC,
                    video_resolution = 720,
                    optimized_for_streaming = True
                )
            ]
    )

    if include_container:
        return ObjectContainer(objects=[videoclip_obj])
    else:
        return videoclip_obj

####################################################################################################
@indirect
def PlayVideo(url, **kwargs):

    return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(url))

####################################################################################################
@route(PREFIX + '/getdata')
def GetData(url):

	# Quick and dirty workaround to get this to work on Windows
	# Do not validate ssl certificate
	# http://stackoverflow.com/questions/27835619/ssl-certificate-verify-failed-error
	if 'Windows' in Platform.OS:
		req = urllib2.Request(url, headers=HTTP_HEADERS)
		ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
		data = urllib2.urlopen(req, context=ssl_context).read()
	else:
		data = HTTP.Request(url, headers=HTTP_HEADERS).content

	return data

####################################################################################################
# Convert a time string into seconds integer
def ToSeconds(timestr):

    seconds= 0
    for part in timestr.split(':'):
        seconds= seconds*60 + int(part)
    return seconds
