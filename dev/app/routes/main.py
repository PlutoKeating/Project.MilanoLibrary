from flask import Blueprint, render_template, request
from app.services.video_processor import VideoProcessor
from app.models.MilanoBook.storage import MilanoBookStorage

# 创建蓝图
bp = Blueprint('main', __name__)

# 初始化视频处理器和存储管理器
processor = VideoProcessor()
storage = MilanoBookStorage()

@bp.route('/')
def index():
    """首页，显示视频URL输入表单"""
    return render_template('index.html')

@bp.route('/process', methods=['POST'])
def process_video():
    """处理视频，显示结果页面"""
    video_url = request.form['video_url']
    
    try:
        # 处理视频
        print(f"开始处理视频：{video_url}")
        milano_book, video_path, audio_path = processor.process_video(video_url)
        print(f"视频处理完成，生成了{len(milano_book.paragraphs)}个段落")
        
        # 保存到本地存储
        print(f"开始保存到本地存储")
        book_id = storage.save_book(milano_book, video_path=video_path, audio_path=audio_path)
        print(f"保存成功，书籍ID：{book_id}")
        
        # 转换为可序列化的结果
        result = {
            'title': milano_book.title,
            'author': milano_book.author,
            'source_url': milano_book.source_url,
            'paragraphs': [
                {
                    'start_time': p.start_time,
                    'end_time': p.end_time,
                    'text_content': p.text_content,
                    'multi_modal_data': p.multi_modal_data
                } for p in milano_book.paragraphs
            ],
            'items': [
                {
                    'type': item.__class__.__name__,
                    'name': item.name,
                    'description': item.description,
                    'content_count': len(item.content) if hasattr(item, 'content') else (len(item.nodes) if hasattr(item, 'nodes') else 0)
                } for item in milano_book.items
            ]
        }
        
        print(f"渲染结果页面")
        return render_template('result.html', result=result)
    except Exception as e:
        print(f"处理失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return f"处理失败：{str(e)}", 500

@bp.route('/notes')
def view_notes_list():
    """查看所有生成的笔记"""
    return render_template('notes_list.html')

@bp.route('/notes/<notes_id>')
def view_notes(notes_id):
    """查看生成的笔记"""
    return render_template('notes.html', notes_id=notes_id)

@bp.route('/books')
def view_books():
    """查看所有书籍"""
    return render_template('books.html')
