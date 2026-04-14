CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL,
    title TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL,
    conversation_id INT,
    user_message TEXT,
    bot_response TEXT
);