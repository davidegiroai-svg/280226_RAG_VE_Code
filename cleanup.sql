DELETE FROM chunks WHERE kb_namespace='test_kb';
DELETE FROM documents WHERE kb_id=(SELECT id FROM knowledge_base WHERE namespace='test_kb');
DELETE FROM knowledge_base WHERE namespace='test_kb';
