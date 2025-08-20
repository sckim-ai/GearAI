from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import re
from dotenv import load_dotenv
import os
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3'

# Create MCP Server
mcp = FastMCP("youtube_agent_server")

## Tool 1: 유투브 영상 Url에 대한 자막을 가져옵니다.
@mcp.tool()
def get_youtube_transcript(url: str) -> str:
    """유투브 영상 URL에 대한 자막을 가져옵니다."""
    # 1. 유투브 URL에서 비디오 ID를 추출합니다.
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if not video_id_match:
        raise ValueError("올바른 YouTube URL이 아닙니다.")
    
    video_id = video_id_match.group(1)
    language = ["ko", "en"]
    try:
        # 2. 자막을 가져옵니다.
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=language)
        
        # 3. 자막을 문자열로 변환합니다.
        full_transcript = " ".join([entry['text'] for entry in transcript])
        
        return full_transcript
    except Exception as e:
        raise RuntimeError(f"비디오 ID: {video_id} 에 대한 자막을 찾을 수 없거나 사용할 수 없습니다. {str(e)}")

## Tool 2: 유투브에서 특정 키워드로 동영상을 검색하고 세부 정보를 가져옵니다.
@mcp.tool()
def search_youtube_videos(query: str) -> list:
    """유투브에서 특정 키워드로 동영상을 검색하고 세부 정보를 가져옵니다."""
    try:
        # 1. 동영상 검색
        max_results: int = 20
        search_url = f"{YOUTUBE_API_URL}/search?part=snippet&q={requests.utils.quote(query)}&type=video&maxResults={max_results}&key={YOUTUBE_API_KEY}"
        print(f"Searching YouTube with URL: {search_url}")

        search_response = requests.get(search_url)
        search_data = search_response.json()
        video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]

        if not video_ids:
            print("No videos found for the query.")
            return []

        video_details_url = f"{YOUTUBE_API_URL}/videos?part=snippet,statistics&id={','.join(video_ids)}&key={YOUTUBE_API_KEY}"
        print(f"영상 정보 가져오는 중: {video_details_url}")
        details_response = requests.get(video_details_url)
        details_response.raise_for_status()
        details_data = details_response.json()

        videos = []
        for item in details_data.get('items', []):
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            thumbnails = snippet.get('thumbnails', {})
            high_thumbnail = thumbnails.get('high', {}) 
            view_count = statistics.get('viewCount')
            like_count = statistics.get('likeCount')

            video_card = {
                "title": snippet.get('title', 'N/A'),
                "publishedDate": snippet.get('publishedAt', ''),
                "channelName": snippet.get('channelTitle', 'N/A'),
                "channelId": snippet.get('channelId', ''),
                "thumbnailUrl": high_thumbnail.get('url', ''),
                "viewCount": int(view_count) if view_count is not None else None,
                "likeCount": int(like_count) if like_count is not None else None,
                "url": f"https://www.youtube.com/watch?v={item.get('id', '')}",
            }
            videos.append(video_card)

        if not videos:
            print("No video details could be fetched.")
            return []

        return videos

    except Exception as e:
        print(f"Error: {e}")
        return []
                
### Tool 3 : YouTube 동영상 URL로부터 채널 정보와 최근 5개의 동영상을 가져옵니다
@mcp.tool()
def get_channel_info(video_url: str) -> dict:
    """YouTube 동영상 URL로부터 채널 정보와 최근 5개의 동영상을 가져옵니다"""
    def extract_video_id(url):
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
        return match.group(1) if match else None

    def fetch_recent_videos(channel_id):
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            response = requests.get(rss_url)
            if response.status_code != 200:
                return []

            root = ET.fromstring(response.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            videos = []

            for entry in root.findall('.//atom:entry', ns)[:5]:  
                title = entry.find('./atom:title', ns).text
                link = entry.find('./atom:link', ns).attrib['href']
                published = entry.find('./atom:published', ns).text
                videos.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'updatedDate': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            return videos
        except:
            return []

    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    video_api = f"{YOUTUBE_API_URL}/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}"
    video_data = requests.get(video_api).json()
    if not video_data.get('items'):
        raise ValueError("No video found")

    video_info = video_data['items'][0]
    channel_id = video_info['snippet']['channelId']

    channel_api = f"{YOUTUBE_API_URL}/channels?part=snippet,statistics&id={channel_id}&key={YOUTUBE_API_KEY}"
    channel_data = requests.get(channel_api).json()['items'][0]

    return {
        'channelTitle': channel_data['snippet']['title'],
        'channelUrl': f"https://www.youtube.com/channel/{channel_id}",
        'subscriberCount': channel_data['statistics'].get('subscriberCount', '0'),
        'viewCount': channel_data['statistics'].get('viewCount', '0'),
        'videoCount': channel_data['statistics'].get('videoCount', '0'),
        'videos': fetch_recent_videos(channel_id)
    }


if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run()