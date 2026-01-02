from flask import Blueprint, request, jsonify
from app.services.video_processor import VideoProcessor
from app.models.MilanoBook.storage import MilanoBookStorage
from app.services.generate_service import GenerateService
import uuid
import os
from datetime import datetime
import json

# 创建蓝图，url_prefix表示所有API路由都以/api开头
bp = Blueprint('api', __name__, url_prefix='/api')

# 初始化视频处理器和存储管理器
processor = VideoProcessor()
storage = MilanoBookStorage()

@bp.route('/process', methods=['POST'])
def api_process_video():
    """处理视频，返回JSON格式结果"""
    data = request.json
    video_url = data.get('video_url')
    
    if not video_url:
        return jsonify({'error': '缺少video_url参数'}), 400
    
    try:
        # 处理视频
        milano_book, video_path, audio_path = processor.process_video(video_url)
        
        # 保存到本地存储
        book_id = storage.save_book(milano_book, video_path=video_path, audio_path=audio_path)
        
        # 转换为JSON格式，确保所有对象都被正确序列化
        paragraphs_data = []
        for p in milano_book.paragraphs:
            paragraphs_data.append({
                'start_time': p.start_time,
                'end_time': p.end_time,
                'text_content': p.text_content,
                'multi_modal_data': p.multi_modal_data
            })
        
        items_data = []
        for item in milano_book.items:
            item_type = item.__class__.__name__
            content_count = 0
            if hasattr(item, 'content'):
                content_count = len(item.content)
            elif hasattr(item, 'nodes'):
                content_count = len(item.nodes)
            
            items_data.append({
                'type': item_type,
                'name': item.name,
                'description': item.description,
                'content_count': content_count
            })
        
        result = {
            'book_id': book_id,
            'title': milano_book.title,
            'author': milano_book.author,
            'source_url': milano_book.source_url,
            'paragraphs': paragraphs_data,
            'items': items_data
        }
        
        return jsonify(result)
    except Exception as e:
        print(f"API处理失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/books', methods=['GET'])
def api_list_books():
    """列出所有存储的书籍"""
    try:
        books = storage.list_books()
        return jsonify({'books': books})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/books/<book_id>', methods=['GET'])
def api_get_book(book_id):
    """获取指定书籍的详细信息"""
    try:
        milano_book = storage.load_book(book_id)
        
        # 转换为JSON格式，确保所有对象都被正确序列化
        paragraphs_data = []
        for p in milano_book.paragraphs:
            paragraphs_data.append({
                'start_time': p.start_time,
                'end_time': p.end_time,
                'text_content': p.text_content,
                'multi_modal_data': p.multi_modal_data
            })
        
        items_data = []
        for item in milano_book.items:
            item_type = item.__class__.__name__
            content_count = 0
            if hasattr(item, 'content'):
                content_count = len(item.content)
            elif hasattr(item, 'nodes'):
                content_count = len(item.nodes)
            
            items_data.append({
                'type': item_type,
                'name': item.name,
                'description': item.description,
                'content_count': content_count
            })
        
        result = {
            'book_id': book_id,
            'title': milano_book.title,
            'author': milano_book.author,
            'source_url': milano_book.source_url,
            'paragraphs': paragraphs_data,
            'items': items_data
        }
        
        return jsonify(result)
    except FileNotFoundError:
        return jsonify({'error': f'书籍 {book_id} 不存在'}), 404
    except Exception as e:
        print(f"API获取书籍失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/books/<book_id>', methods=['DELETE'])
def api_delete_book(book_id):
    """删除指定书籍"""
    try:
        success = storage.delete_book(book_id)
        if success:
            return jsonify({'message': f'书籍 {book_id} 已删除'})
        else:
            return jsonify({'error': f'书籍 {book_id} 不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/generate-notes', methods=['POST'])
def api_generate_notes():
    """批量生成笔记"""
    try:
        data = request.json
        book_ids = data.get('book_ids', [])
        user_prompt = data.get('user_prompt', '')
        
        if not book_ids:
            return jsonify({'error': '缺少book_ids参数'}), 400
        
        if not isinstance(book_ids, list):
            return jsonify({'error': 'book_ids必须是数组'}), 400
        
        milano_books_data = []
        for book_id in book_ids:
            milano_book = storage.load_book(book_id)
            
            paragraphs_data = []
            for p in milano_book.paragraphs:
                paragraphs_data.append({
                    'start_time': p.start_time,
                    'end_time': p.end_time,
                    'text_content': p.text_content,
                    'multi_modal_data': p.multi_modal_data
                })
            
            items_data = []
            for item in milano_book.items:
                item_type = item.__class__.__name__
                content_count = 0
                if hasattr(item, 'content'):
                    content_count = len(item.content)
                elif hasattr(item, 'nodes'):
                    content_count = len(item.nodes)
                
                items_data.append({
                    'type': item_type,
                    'name': item.name,
                    'description': item.description,
                    'content_count': content_count
                })
            
            milano_books_data.append({
                'book_id': book_id,
                'title': milano_book.title,
                'author': milano_book.author,
                'source_url': milano_book.source_url,
                'paragraphs': paragraphs_data,
                'items': items_data
            })
        
        generate_service = GenerateService()
        notes_content = generate_service.generate_notes(milano_books_data, user_prompt)
        
        notes_id = str(uuid.uuid4())
        notes_path = f"notes/{notes_id}.json"
        
        notes_data = {
            'notes_id': notes_id,
            'book_ids': book_ids,
            'content': notes_content,
            'user_prompt': user_prompt,
            'created_at': datetime.now().isoformat()
        }
        
        os.makedirs('notes', exist_ok=True)
        with open(notes_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(notes_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'notes_id': notes_id,
            'message': '笔记生成成功'
        })
    except FileNotFoundError as e:
        return jsonify({'error': f'书籍不存在：{str(e)}'}), 404
    except Exception as e:
        print(f"生成笔记失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/generate-notes-stream', methods=['POST'])
def api_generate_notes_stream():
    """批量生成笔记（流式输出）"""
    try:
        data = request.json
        book_ids = data.get('book_ids', [])
        user_prompt = data.get('user_prompt', '')
        
        if not book_ids:
            return jsonify({'error': '缺少book_ids参数'}), 400
        
        if not isinstance(book_ids, list):
            return jsonify({'error': 'book_ids必须是数组'}), 400
        
        milano_books_data = []
        for book_id in book_ids:
            milano_book = storage.load_book(book_id)
            
            paragraphs_data = []
            for p in milano_book.paragraphs:
                paragraphs_data.append({
                    'start_time': p.start_time,
                    'end_time': p.end_time,
                    'text_content': p.text_content,
                    'multi_modal_data': p.multi_modal_data
                })
            
            items_data = []
            for item in milano_book.items:
                item_type = item.__class__.__name__
                content_count = 0
                if hasattr(item, 'content'):
                    content_count = len(item.content)
                elif hasattr(item, 'nodes'):
                    content_count = len(item.nodes)
                
                items_data.append({
                    'type': item_type,
                    'name': item.name,
                    'description': item.description,
                    'content_count': content_count
                })
            
            milano_books_data.append({
                'book_id': book_id,
                'title': milano_book.title,
                'author': milano_book.author,
                'source_url': milano_book.source_url,
                'paragraphs': paragraphs_data,
                'items': items_data
            })
        
        generate_service = GenerateService()
        
        # 设置流式响应
        def generate():
            notes_id = str(uuid.uuid4())
            notes_content = ""
            
            # 流式生成内容
            for chunk in generate_service.generate_notes_stream(milano_books_data, user_prompt):
                notes_content += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            
            # 保存完整笔记
            notes_path = f"notes/{notes_id}.json"
            notes_data = {
                'notes_id': notes_id,
                'book_ids': book_ids,
                'content': notes_content,
                'user_prompt': user_prompt,
                'created_at': datetime.now().isoformat()
            }
            
            os.makedirs('notes', exist_ok=True)
            with open(notes_path, 'w', encoding='utf-8') as f:
                json.dump(notes_data, f, ensure_ascii=False, indent=2)
            
            # 发送结束信号
            yield f"data: {json.dumps({'type': 'done', 'notes_id': notes_id})}\n\n"
        
        from flask import Response
        return Response(generate(), mimetype='text/event-stream')
    except FileNotFoundError as e:
        return jsonify({'error': f'书籍不存在：{str(e)}'}), 404
    except Exception as e:
        print(f"生成笔记失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/notes', methods=['GET'])
def api_list_notes():
    """获取所有生成的笔记"""
    try:
        notes_dir = 'notes'
        notes = []
        
        if os.path.exists(notes_dir):
            for filename in os.listdir(notes_dir):
                if filename.endswith('.json'):
                    notes_path = os.path.join(notes_dir, filename)
                    with open(notes_path, 'r', encoding='utf-8') as f:
                        notes_data = json.load(f)
                        notes.append(notes_data)
        
        # 按创建时间倒序排序
        notes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'notes': notes
        })
    except Exception as e:
        print(f"获取笔记列表失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/notes/<notes_id>', methods=['GET'])
def api_get_notes(notes_id):
    """获取生成的笔记"""
    try:
        notes_path = f"notes/{notes_id}.json"
        
        if not os.path.exists(notes_path):
            return jsonify({'error': f'笔记 {notes_id} 不存在'}), 404
        
        with open(notes_path, 'r', encoding='utf-8') as f:
            import json
            notes_data = json.load(f)
        
        return jsonify({
            'success': True,
            'notes': notes_data
        })
    except Exception as e:
        print(f"获取笔记失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/notes/<notes_id>', methods=['DELETE'])
def api_delete_notes(notes_id):
    """删除指定笔记"""
    try:
        notes_path = f"notes/{notes_id}.json"
        
        if not os.path.exists(notes_path):
            return jsonify({'error': f'笔记 {notes_id} 不存在'}), 404
        
        os.remove(notes_path)
        
        return jsonify({
            'success': True,
            'message': f'笔记 {notes_id} 已删除'
        })
    except Exception as e:
        print(f"删除笔记失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
