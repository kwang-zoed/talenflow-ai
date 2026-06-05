import sys
sys.path.insert(0, '.')

print("=" * 60)
print("Checking imports...")
print("=" * 60)

from app.utils.llm_utils import ParseMode, get_parse_prompt, parse_llm_json_result
print('[1] llm_utils OK, ParseMode.SINGLE =', ParseMode.SINGLE)

from app.utils.data_cleaner import clean_skills_data, clean_job_data_for_response, clean_batch_job_results
print('[2] data_cleaner OK, clean_skills_data(None) =', clean_skills_data(None))
print('    clean_skills_data(["Java", "Python"]) =', clean_skills_data(["Java", "Python"]))

prompt = get_parse_prompt('test content', ParseMode.SINGLE)
print('[3] Prompt SINGLE length:', len(prompt))

prompt_batch = get_parse_prompt('test content', ParseMode.BATCH)
print('[4] Prompt BATCH length:', len(prompt_batch))

from app.utils.document_parser import extract_text_from_bytes
print('[5] document_parser OK')

from app.core import security
print('[6] security OK, hash prefix:', security.get_password_hash('test')[:20])

print("\n=== ALL CHECK PASSED ===")
