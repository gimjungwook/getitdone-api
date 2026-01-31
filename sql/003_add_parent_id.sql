-- parent_id: 이 assistant 메시지가 속한 user 메시지 ID
ALTER TABLE opencode_messages
ADD COLUMN parent_id text REFERENCES opencode_messages(id) DEFAULT NULL;

-- finish: 이 step의 종료 이유 ("tool_calls", "stop", "end_turn" 등)
ALTER TABLE opencode_messages
ADD COLUMN finish text DEFAULT NULL;

-- 인덱스: parent_id로 그룹 조회 성능
CREATE INDEX idx_opencode_messages_parent_id ON opencode_messages(parent_id);
