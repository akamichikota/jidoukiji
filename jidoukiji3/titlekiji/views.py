# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
import json
import asyncio
from asgiref.sync import async_to_sync
from asgiref.sync import sync_to_async
import aiohttp
import logging


# ロガーの設定
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# OpenAI APIクライアントの設定
client = OpenAI(api_key='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')

# WordPressの設定情報を保存するビュー
@require_http_methods(["GET", "POST"])
def wordpress_settings(request):
    if request.method == 'POST':
        # フォームから送信されたデータをセッションに保存
        request.session['wordpress_username'] = request.POST.get('wordpress_username')
        request.session['wordpress_password'] = request.POST.get('wordpress_password')
        request.session['wordpress_url'] = request.POST.get('wordpress_url')
        
        messages.success(request, 'WordPress設定が保存されました。')
        return redirect('wordpress_settings')

    return render(request, 'wordpress_settings_form.html')



def titlekiji_form(request):
    # 記事生成フォームを表示するビュー
    return render(request, 'titlekiji_form.html')

def settings_form(request):
    # 記事生成フォームを表示するビュー
    return render(request, 'wordpress_settings_form.html')

# 同期コードで WordPress の情報を取得する関数を定義
@sync_to_async
def get_wordpress_info(request):

    wordpress_username = request.session.get('wordpress_username')
    wordpress_password = request.session.get('wordpress_password')
    wordpress_url = request.session.get('wordpress_url')
    return wordpress_username, wordpress_password, wordpress_url

@csrf_exempt
@require_http_methods(["POST"])
async def generate_articles_async(request):
    logger.info("Received request for article generation")
    if not request.body:
        logger.warning("Request body is empty")
        return JsonResponse({'error': 'Empty request body'}, status=400)

    wordpress_username, wordpress_password, wordpress_url = await get_wordpress_info(request)
    

    # 設定が未設定の場合のエラー処理
    if not all([wordpress_username, wordpress_password, wordpress_url]):
        logger.error("WordPress settings not configured")
        return JsonResponse({'error': 'WordPress settings not configured'}, status=400)

    try:
        data = json.loads(request.body)
        title_keyword_pairs = data.get('title_keyword_pairs')
        post_status = data.get('post_status', 'draft') # デフォルトは 'draft'
        
        if not title_keyword_pairs or not isinstance(title_keyword_pairs, list):
            logger.error("Invalid or missing title-keyword pairs")
            return JsonResponse({'error': 'Invalid or missing title-keyword pairs'}, status=400)

        
        # タイトルとキーワードのペアを処理
        articles = await generate_and_post_articles_to_wordpress(title_keyword_pairs, post_status, request)
        successful_posts = [
            {
                'title': article.get('title', '無題'),
                'content': article.get('content', ''),
                'status': article.get('status'),
                'message': article.get('message')
            } for article in articles if article.get('status') == 'success'
        ]
        failed_posts = [
            article for article in articles if article.get('status') == 'failed'
        ]

        return JsonResponse({
            'articles': successful_posts,
            'failed': len(failed_posts),
            'failed_messages': [article['message'] for article in failed_posts]
        })
    except json.JSONDecodeError as e:
        logger.error(f'JSON Decode Error: {e}', exc_info=True)
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f'Internal Server Error: {e}', exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
    
generate_articles = async_to_sync(generate_articles_async)

async def generate_and_post_articles_to_wordpress(title_keyword_pairs, post_status, request):
    # 関数内で WordPress の情報を非同期に取得
    wordpress_username, wordpress_password, wordpress_url = await get_wordpress_info(request)

    articles = []
    for pair in title_keyword_pairs:
        title, keywords = pair.get('title'), pair.get('keywords')
        response = await get_html_article_from_gpt(title, keywords)
        if response:
            article_post_response = await post_to_wordpress(title, response, post_status, wordpress_username, wordpress_password, wordpress_url)
            articles.append(article_post_response)
        else:
            articles.append({'status': 'failed', 'message': f'Failed to generate article for {title}'})
    return articles

async def get_html_article_from_gpt(title, keywords):
    try:
        # キーワードが提供されていない場合は、キーワードに関する指示を省略
        keyword_instruction = f"・キーワード： '{keywords}'を可能な限り記事全体に織り交ぜてください。特に文章の前半には多めに'{keywords}'を使ってください。" if keywords else ""

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo-1106",
            messages=[{
                "role": "system", 
                "content": f"""
                あなたは人間心理とコピーライティングに詳しい、記事ライターのエキスパートです。
                タイトル「{title}」に対応する記事を、必ずHTML形式で作成してください。以下の点を考慮してください：
                ・{keyword_instruction}
                ・内容：記事の書き出しは問題提起と共感を書いて、その後に問題解決策を書いてください。
                ・スタイル：プロフェッショナルで分かりやすく、なおかつ読者が親しみやすいような話し方にしてください。読み手のことは「皆さん」ではなく「あなた」と書いてください。
                ・形式：見出しを適切に用い、全体の文字数は最低2000文字以上にしてください。
                ・その他：あなたがAIであることは絶対に読者にばれないようにしてください。また、以下に記載しているデザインのフォーマットを参考にしてください。
                    
                
                    ###デザインのフォーマット###
                    <p>問題提起と共感を得る導入文（最低150文字以上）</p><br>

                    <h2>タイトル1</h2>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>

                    <h2>タイトル2</h2><br>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>

                    <h2>タイトル3</h2><br>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p>
                    <h4>小見出し</h4>
                    <p>※最低150文字以上の内容</p><br>

                    <p>締めくくりの文章（※最低150文字以上の内容）</p>

                """
            }]
        )
        if response:
            html_content = response.choices[0].message.content.strip()
            logger.debug(f"Generated HTML content for {title}: {html_content}")
            if not html_content:
                logger.error(f"No HTML content generated for {title}")
            return html_content
        else:
            logger.error(f"No response from GPT for {title}")
            return None
    except Exception as e:
        logger.error(f'Error generating article for {title}: {e}', exc_info=True)
        return None

async def post_to_wordpress(title, html_content, post_status, wordpress_username, wordpress_password, wordpress_url):
    headers = {'Content-Type': 'application/json'}
    post_data = {'title': title, 'content': html_content, 'status': post_status}

    async with aiohttp.ClientSession() as session:
        async with session.post(wordpress_url, json=post_data, 
                                auth=aiohttp.BasicAuth(wordpress_username, wordpress_password), 
                                headers=headers) as response:
            if response.status == 201:
                return {'status': 'success', 'message': f'Article posted successfully: {title}', 'title': title, 'content': html_content }
            else:
                response_text = await response.text()
                logger.error(f'Failed to post article {title}: {response.status}, {response_text}', exc_info=True)
                return {'status': 'failed', 'message': f'Failed to post article: {title}'}


