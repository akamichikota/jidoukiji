# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import openai
from openai import OpenAI
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import json
import asyncio
from asgiref.sync import async_to_sync
import aiohttp
import logging
from django.template import loader  # テンプレートをロードするためのimport
from django.utils.html import mark_safe


# ロガーの設定
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# JSONデータをHTMLに変換する関数

def json_to_html(article_data):
    html_content = ""
    
    # タイトルの処理
    if 'title' in article_data:
        html_content += f"<h1>{mark_safe(article_data['title'])}</h1>\n"

    # 導入部の処理
    if 'introduction' in article_data:
        html_content += f"<p>{mark_safe(article_data['introduction'])}</p>\n"

    if 'heading' in article_data:
        html_content += f"<h2>{mark_safe(article_data['heading'])}</h2>\n"
    if 'content' in article_data:
        html_content += f"<p>{mark_safe(article_data['content'])}</p>\n"
    if 'list' in article_data:
        list_items = "".join(f"<li>{mark_safe(item)}</li>\n" for item in article_data['list'])
        html_content += f"<ul>\n{list_items}</ul>\n"
    
    if 'heading' in section:
        html_content += f"<h2>{mark_safe(section['heading'])}</h2>\n"
    if 'content' in section:
        html_content += f"<p>{mark_safe(section['content'])}</p>\n"
    if 'list' in section:
        list_items = "".join(f"<li>{mark_safe(item)}</li>\n" for item in section['list'])
        html_content += f"<ul>\n{list_items}</ul>\n"

    # セクションの処理
    for section in article_data.get('sections', []):
        if isinstance(section, dict):
            if 'heading' in section:
                html_content += f"<h2>{mark_safe(section['heading'])}</h2>\n"
            if 'content' in section:
                html_content += f"<p>{mark_safe(section['content'])}</p>\n"
            if 'list' in section:
                list_items = "".join(f"<li>{mark_safe(item)}</li>\n" for item in section['list'])
                html_content += f"<ul>\n{list_items}</ul>\n"

    return html_content




def json_to_html(item):
    html_content = ""
    
    # タイトルの処理
    if 'title' in item:
        html_content += f"<h1>{mark_safe(item['title'])}</h1>\n"

    # 導入部の処理
    if 'introduction' in item:
        html_content += f"<p>{mark_safe(item['introduction'])}</p>\n"

    if 'heading' in item:
        html_content += f"<h2>{mark_safe(item['heading'])}</h2>\n"
    if 'content' in item:
        html_content += f"<p>{mark_safe(item['content'])}</p>\n"
    if 'list' in item:
        list_items = "".join(f"<li>{mark_safe(list_item)}</li>\n" for list_item in item['list'])
        html_content += f"<ul>\n{list_items}</ul>\n"

    # セクションの処理
    if 'sections' in item:
        for section in item['sections']:
            if 'heading' in section:
                html_content += f"<h2>{mark_safe(section['heading'])}</h2>\n"
            if 'content' in section:
                html_content += f"<p>{mark_safe(section['content'])}</p>\n"
            if 'list' in section:
                list_items = "".join(f"<li>{mark_safe(list_item)}</li>\n" for list_item in section['list'])
                html_content += f"<ul>\n{list_items}</ul>\n"

    return html_content





# WordPressの設定情報
wordpress_username = 'kota'
wordpress_password = 'u1DN Tfj4 qvYn ldlR d93E Hvg3'
wordpress_url = 'https://the-raku.com/wp-json/wp/v2/posts'

# OpenAI APIクライアントの設定
client = OpenAI(api_key='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')

def titlekiji_form(request):
    # 記事生成フォームを表示するビュー
    return render(request, 'titlekiji_form.html')

@csrf_exempt
@require_http_methods(["POST"])
async def generate_articles_async(request):
    logger.info("Received request for article generation")

    # リクエストボディの内容をログに出力
    logger.debug(f"Request body: {request.body}")

    if not request.body:
        logger.warning("Request body is empty")
        return JsonResponse({'error': 'Empty request body'}, status=400)

    try:
        # JSONデータの解析
        data = json.loads(request.body)
        titles = data.get('titles')
        logger.info(f"Titles received: {titles}")

        if not titles or not isinstance(titles, list):
            return JsonResponse({'error': 'Invalid or missing titles'}, status=400)

        results = await generate_and_post_articles_to_wordpress(titles)
        # 生成結果をログに出力
        logger.debug(f"Generated articles: {results}")

        successful_posts = [result for result in results if result['status']]
        failed_posts = [result for result in results if not result['status']]

        return JsonResponse({
            'articles': [{'title': article['title'], 'content': article['content']} for article in successful_posts],
            'failed': f'Failed to post {len(failed_posts)} articles.',
            'failed_messages': [result['message'] for result in failed_posts]
        })

    except json.JSONDecodeError as e:
        error_message = f'JSON Decode Error: Invalid JSON format in request body. Error: {e}'
        logger.error(error_message, exc_info=True)
        return JsonResponse({'error': error_message}, status=400)

    except Exception as e:
        error_message = f'Internal Server Error: {type(e).__name__}, Message: {e}'
        logger.error(error_message, exc_info=True)
        return JsonResponse({'error': error_message}, status=500)


# 同期関数としてのエンドポイントを定義
generate_articles = async_to_sync(generate_articles_async)

async def post_to_wordpress(article):
    logger.info(f"Trying to post article to WordPress: {article['title']}")
    headers = {'Content-Type': 'application/json'}
    
    post_data = {
        'title': article['title'],
        'content': article['content'],  # 直接 content_html を使用
        'status': 'publish'
    }

    # WordPressへの投稿前
    logger.debug(f"Article data being sent to WordPress: {post_data}")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            wordpress_url,
            json=post_data,
            auth=aiohttp.BasicAuth(wordpress_username, wordpress_password),
            headers=headers
            ) as response:
            
            response_text = await response.text()

            if response.status == 201:
                logger.info(f"Article posted successfully: {article['title']}")
                return {'status': True, 'message': 'Article posted successfully'}
            else:
                error_message = f"Failed to post article to WordPress. Title: '{article['title']}', Status: {response.status}, Response: {response_text}"
                logger.error(error_message)
                return {'status': False, 'message': error_message}

async def generate_and_post_articles_to_wordpress(titles):
    logger.info(f"Generating and posting articles for titles: {titles}")
    articles = []
    for title in titles:
        try:
            response = await asyncio.to_thread(         
                client.chat.completions.create,
                model="gpt-3.5-turbo-1106",
                response_format={"type": "json_object"},
                messages=[{
                    "role": "system", 
                    "content": f"""
                    タイトル「{title}」に関連する記事を必ず「JSON形式の辞書型」で作成してください。以下の点を考慮してください：
                    ・キーワード： '{title}'に関連するキーワードを記事全体に織り交ぜてください。
                    ・内容：読者が共感しやすいように、リード文で関心を引きつけてください。
                    ・スタイル：プロフェッショナルでわかりやすい説明を心がけてください。また、読者が親しみやすいような話し方にしてください。
                    ・形式：見出しを適切に用い、全体の文字数は最低2000文字以上にしてください。また、20~30文字で必ず改行してください。
                    ・その他：WordPressに投稿するため、H2, H3タグ、<br>タグを適切に使用してください。

                    ## 制約条件 
                    ・ 必ず半角のJSON形式の辞書型で出力すること
                    """
                }]
            )

            response_content = response.choices[0].message.content.strip()
            # レスポンスの内容をJSONオブジェクトに変換
            article_data = json.loads(response_content)

            # データがリスト型の場合の処理
            if isinstance(article_data, list):
                for item in article_data:
                    content_html = json_to_html(item)
                    article = {
                        'title': title,
                        'content': content_html,
                        'status': 'publish'
                    }
                    articles.append(article)
            else:
                # データが辞書型の場合の処理
                content_html = json_to_html(article_data)
                article = {
                    'title': title,
                    'content': content_html,
                    'status': 'publish'
                }
                articles.append(article)

        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error for title '{title}': {e}")
            continue
        except (KeyError, ValueError) as e:
            logger.error(f"Error processing content for title '{title}': {e}")
            continue
        except Exception as e:
            logger.error(f"Unhandled error for title '{title}': {type(e).__name__}, Message: {e}")
            continue

    
    # WordPressへの投稿
    tasks = [post_to_wordpress(article) for article in articles]
    results = await asyncio.gather(*tasks)
    successful_posts = [article for article, result in zip(articles, results) if result['status']]
    logger.debug(f"Generated articles being returned: {successful_posts}")
    
    return successful_posts

