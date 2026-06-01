import os
import pickle
import time
import faiss
import numpy as np
from typing import List, Dict
from app.models.job_position import JobPosition

from app.rag.embeddings import embed_documents, get_vector_dimension

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'vector_store')
INDEX_FILE = os.path.join(VECTOR_STORE_DIR, 'index.faiss')
METADATA_FILE = os.path.join(VECTOR_STORE_DIR, 'metadata.pkl')

_vectorstore = None


def add_job_to_vectorstore(db_job: JobPosition):
    print(f"\n{'=' * 60}")
    print(f"[VECTOR STORE DEBUG] 职位创建成功，开始写入向量库...")
    print(f"[VECTOR STORE DEBUG] 职位ID: {db_job.id}")
    print(f"[VECTOR STORE DEBUG] 职位标题: {db_job.title}")

    try:
        skills_text = ' '.join(db_job.required_skills) if db_job.required_skills else ''
        full_text = f"{db_job.title} {db_job.company} {db_job.description} {skills_text} {db_job.location or ''} {db_job.experience_requirement or ''} {db_job.education_requirement or ''}"

        texts = [full_text]
        metadatas = [{
            "id": db_job.id,
            "title": db_job.title,
            "company": db_job.company,
            "type": "job"
        }]

        print(f"[VECTOR STORE DEBUG] 待索引文本长度: {len(full_text)}")
        print(f"[VECTOR STORE DEBUG] 元数据: {metadatas}")

        add_texts_to_vectorstore(texts, metadatas)

        print(f"[VECTOR STORE DEBUG] 职位信息成功写入向量库")
        print(f"{'=' * 60}")
    except Exception as e:
        print(f"[VECTOR STORE ERROR] 写入向量库失败: {str(e)}")
        print(f"[VECTOR STORE WARNING] 职位创建成功，但向量库写入失败，不影响主流程")
        import traceback
        traceback.print_exc()


def ensure_dir():
    if not os.path.exists(VECTOR_STORE_DIR):
        os.makedirs(VECTOR_STORE_DIR)
        print(f"[VECTOR STORE DEBUG] 创建向量库目录: {VECTOR_STORE_DIR}")


def get_vectorstore() -> Dict:
    global _vectorstore
    if _vectorstore is None:
        print(f"\n{'='*60}")
        print("[VECTOR STORE DEBUG] 开始获取/初始化FAISS向量库 (IndexIDMap2)...")
        start_time = time.time()
        
        ensure_dir()
        dimension = get_vector_dimension()
        print(f"[VECTOR STORE DEBUG] 向量维度: {dimension}")
        
        if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
            try:
                print(f"[VECTOR STORE DEBUG] 加载已存在的FAISS索引...")
                index = faiss.read_index(INDEX_FILE)
                
                if not hasattr(index, 'remove_ids'):
                    print(f"[VECTOR STORE WARNING] 旧索引格式不支持删除，建议删除 vector_store 目录重建索引")
                
                print(f"[VECTOR STORE DEBUG] 索引加载成功，向量数量: {index.ntotal}")
                
                with open(METADATA_FILE, 'rb') as f:
                    metadatas = pickle.load(f)
                print(f"[VECTOR STORE DEBUG] 元数据加载成功，数量: {len(metadatas)}")
            except Exception as e:
                print(f"[VECTOR STORE WARNING] 加载现有索引失败，重新初始化: {str(e)}")
                base_index = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIDMap2(base_index)
                metadatas = []
        else:
            print(f"[VECTOR STORE DEBUG] 初始化新的FAISS索引 (IndexFlatIP + IndexIDMap2)...")
            base_index = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIDMap2(base_index)
            metadatas = []
        
        _vectorstore = {
            "index": index,
            "embedding_function": embed_documents,
            "metadatas": metadatas
        }
        
        elapsed_time = time.time() - start_time
        print(f"[VECTOR STORE DEBUG] 向量库初始化完成，耗时: {elapsed_time:.2f}s")
        print(f"{'='*60}")
    
    return _vectorstore


def add_texts_to_vectorstore(texts: List[str], metadatas: List[Dict]):
    print(f"\n{'='*60}")
    print(f"[VECTOR STORE DEBUG] 开始向向量库添加文本...")
    print(f"[VECTOR STORE DEBUG] 待添加文本数量: {len(texts)}")
    print(f"[VECTOR STORE DEBUG] 待添加元数据数量: {len(metadatas)}")
    start_time = time.time()
    
    try:
        vectorstore = get_vectorstore()
        index = vectorstore["index"]
        embedding_func = vectorstore["embedding_function"]
        
        if not texts:
            print("[VECTOR STORE DEBUG] 输入文本为空，跳过添加")
            print(f"{'='*60}")
            return
        
        print(f"[VECTOR STORE DEBUG] 开始计算向量...")
        numpy_embeddings = embedding_func(texts)
        numpy_embeddings = np.array(numpy_embeddings).astype('float32')
        
        print(f"[VECTOR STORE DEBUG] 向量计算完成，形状: {numpy_embeddings.shape}")
        
        ids = np.array([m.get('id', idx) for idx, m in enumerate(metadatas)]).astype('int64')
        print(f"[VECTOR STORE DEBUG] 待添加的向量ID: {ids.tolist()}")
        
        print(f"[VECTOR STORE DEBUG] 开始添加到FAISS索引 (带ID)...")
        index.add_with_ids(numpy_embeddings, ids)
        print(f"[VECTOR STORE DEBUG] 添加完成，索引总向量数: {index.ntotal}")
        
        print(f"[VECTOR STORE DEBUG] 处理元数据...")
        all_metadatas = vectorstore["metadatas"]
        all_metadatas.extend(metadatas)
        print(f"[VECTOR STORE DEBUG] 元数据总数: {len(all_metadatas)}")
        
        print(f"[VECTOR STORE DEBUG] 保存索引文件...")
        faiss.write_index(index, INDEX_FILE)
        print(f"[VECTOR STORE DEBUG] 索引文件已保存: {INDEX_FILE}")
        
        print(f"[VECTOR STORE DEBUG] 保存元数据文件...")
        with open(METADATA_FILE, 'wb') as f:
            pickle.dump(all_metadatas, f)
        print(f"[VECTOR STORE DEBUG] 元数据文件已保存: {METADATA_FILE}")
        
        elapsed_time = time.time() - start_time
        print(f"[VECTOR STORE DEBUG] 向向量库添加完成，总耗时: {elapsed_time:.2f}s")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"[VECTOR STORE ERROR] 添加文本失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def remove_job_from_vectorstore(job_id: int) -> bool:
    """
    支持按职位ID删除向量
    :param job_id: 要删除的职位ID
    :return: 是否删除成功
    """
    print(f"\n{'='*60}")
    print(f"[VECTOR STORE DEBUG] 开始删除向量: job_id={job_id}")
    
    try:
        vectorstore = get_vectorstore()
        index = vectorstore["index"]
        
        if not hasattr(index, 'remove_ids'):
            print(f"[VECTOR STORE ERROR] 当前索引不支持删除操作，请删除vector_store目录重建索引")
            print(f"{'='*60}")
            return False
        
        faiss_id = np.array([job_id]).astype('int64')
        n_before = index.ntotal
        index.remove_ids(faiss_id)
        n_after = index.ntotal
        
        if n_before == n_after:
            print(f"[VECTOR STORE WARNING] 向量库中未找到ID={job_id}的向量，没有删除")
        
        all_metadatas = vectorstore["metadatas"]
        vectorstore["metadatas"] = [m for m in all_metadatas if m.get('id') != job_id]
        
        print(f"[VECTOR STORE DEBUG] 元数据: 删除前 {len(all_metadatas)} 条，删除后 {len(vectorstore['metadatas'])} 条")
        
        with open(METADATA_FILE, 'wb') as f:
            pickle.dump(vectorstore["metadatas"], f)
        faiss.write_index(index, INDEX_FILE)
        
        print(f"[VECTOR STORE DEBUG] 删除成功，总向量数: {index.ntotal}")
        print(f"{'='*60}")
        return True
        
    except Exception as e:
        print(f"[VECTOR STORE ERROR] 删除向量失败: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}")
        return False
