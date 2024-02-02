// scripts.js

// CSRFトークン取得のための関数
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }   
    return cookieValue;
}

// ローディングアニメーションを表示する関数
function showLoading(button) {
    button.textContent = '生成中...';
    button.disabled = true;
    button.style.background = 'grey';
}

// ローディングアニメーションを停止する関数
function hideLoading(button) {
    button.textContent = '記事生成';
    button.disabled = false;
    button.style.background = '';
}

// ページが読み込まれたらイベントリスナーを設定
document.addEventListener('DOMContentLoaded', function() {
    var form = document.getElementById('article-form');
    var submitButton = document.getElementById('submit-button');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        showLoading(submitButton);

        var titleKeywordPairs = document.getElementById('title-keyword-pairs').value;
        var pairsArray = titleKeywordPairs.split('\n').map(pair => {
            var parts = pair.split(' - ');
            var title = parts[0].trim();
            var keywords = parts.length > 1 ? parts[1].split(',').map(kw => kw.trim()) : [];
            return { title: title, keywords: keywords };
        });

        var postStatus = document.getElementById('post-status').value;
        var resultDiv = document.getElementById('article-result');
        resultDiv.innerHTML = '';

        // 各記事タイトルの生成リクエストを処理
        for (let pair of pairsArray) {
            try {
                const response = await fetch('/generate_articles/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ title_keyword_pairs: [pair], post_status: postStatus })
                });

                const responseData = await response.json();

                if (response.ok && responseData.articles && responseData.articles.length > 0) {
                    displayArticleTitle(responseData.articles[0], resultDiv);
                } else {
                    throw new Error(`Failed to generate article for ${pair.title}`);
                }
            } catch (error) {
                console.error('Error:', error);
                displayError(pair.title, error.message, resultDiv);
            }
        }

        hideLoading(submitButton);
    });
});

// 記事タイトルを表示する関数
function displayArticleTitle(article, resultDiv) {
    var titleElement = document.createElement('p');
    titleElement.textContent = article.title;
    titleElement.className = 'article-title';
    resultDiv.appendChild(titleElement);
}

// エラーを表示する関数
function displayError(title, message, resultDiv) {
    var errorElement = document.createElement('p');
    errorElement.textContent = `Error generating article for ${title}: ${message}`;
    errorElement.className = 'article-error';
    resultDiv.appendChild(errorElement);
}


