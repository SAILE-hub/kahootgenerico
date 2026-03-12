-- =========================================================
--  TeamKahoot — Schema MySQL compatible
--  Ejecutar en MySQL Workbench o via terminal:
--  mysql -u usuario -p kahootgenerico < schema.sql
-- =========================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS player_answers;
DROP TABLE IF EXISTS session_players;
DROP TABLE IF EXISTS game_sessions;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS topics;
DROP VIEW  IF EXISTS leaderboard;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------
--  USERS
--  avatar: entero 1-8 (cada numero = un emoji en el frontend)
-- ---------------------------------------------------------
CREATE TABLE users (
  id            INT          NOT NULL AUTO_INCREMENT,
  username      VARCHAR(50)  NOT NULL,
  email         VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  avatar        SMALLINT     NOT NULL DEFAULT 1,
  games_played  INT          NOT NULL DEFAULT 0,
  games_won     INT          NOT NULL DEFAULT 0,
  total_score   BIGINT       NOT NULL DEFAULT 0,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email    (email),
  UNIQUE KEY uq_users_username (username)
);

-- ---------------------------------------------------------
--  TOPICS  (3 salas)
--  icon_code:  1=Geografia  2=Ciencia  3=Cine
--  color_code: 1=azul  2=verde  3=naranja
-- ---------------------------------------------------------
CREATE TABLE topics (
  id          INT          NOT NULL AUTO_INCREMENT,
  name        VARCHAR(100) NOT NULL,
  description TEXT,
  icon_code   SMALLINT     NOT NULL DEFAULT 1,
  color_code  SMALLINT     NOT NULL DEFAULT 1,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

-- ---------------------------------------------------------
--  QUESTIONS
--  answer_options: texto JSON ["A","B","C","D"]
--  correct_answer: indice 0-3
--  difficulty_level: 1=facil  2=medio  3=dificil
-- ---------------------------------------------------------
CREATE TABLE questions (
  id               INT      NOT NULL AUTO_INCREMENT,
  topic_id         INT      NOT NULL,
  question_text    TEXT     NOT NULL,
  answer_options   TEXT     NOT NULL,
  correct_answer   SMALLINT NOT NULL,
  time_limit       SMALLINT NOT NULL DEFAULT 20,
  points           INT      NOT NULL DEFAULT 1000,
  difficulty_level SMALLINT NOT NULL DEFAULT 2,
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_questions_topic (topic_id),
  CONSTRAINT fk_questions_topic FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------
--  GAME SESSIONS
--  winner_team: 0=empate  1=Equipo A  2=Equipo B
-- ---------------------------------------------------------
CREATE TABLE game_sessions (
  id              INT         NOT NULL AUTO_INCREMENT,
  room_code       VARCHAR(10) NOT NULL,
  topic_id        INT,
  host_user_id    INT,
  host_name       VARCHAR(50),
  total_questions SMALLINT,
  team_a_score    INT         NOT NULL DEFAULT 0,
  team_b_score    INT         NOT NULL DEFAULT 0,
  winner_team     SMALLINT    NOT NULL DEFAULT 0,
  player_count    SMALLINT    NOT NULL DEFAULT 0,
  started_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at        TIMESTAMP   NULL,
  PRIMARY KEY (id),
  CONSTRAINT fk_sessions_topic FOREIGN KEY (topic_id)     REFERENCES topics(id),
  CONSTRAINT fk_sessions_host  FOREIGN KEY (host_user_id) REFERENCES users(id)
);

-- ---------------------------------------------------------
--  SESSION PLAYERS
-- ---------------------------------------------------------
CREATE TABLE session_players (
  id              INT       NOT NULL AUTO_INCREMENT,
  session_id      INT       NOT NULL,
  user_id         INT,
  guest_name      VARCHAR(50),
  team            SMALLINT  NOT NULL,
  final_score     INT       NOT NULL DEFAULT 0,
  correct_answers SMALLINT  NOT NULL DEFAULT 0,
  is_host         TINYINT(1) NOT NULL DEFAULT 0,
  played_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_sp_session FOREIGN KEY (session_id) REFERENCES game_sessions(id) ON DELETE CASCADE,
  CONSTRAINT fk_sp_user    FOREIGN KEY (user_id)    REFERENCES users(id)
);

-- ---------------------------------------------------------
--  PLAYER ANSWERS
-- ---------------------------------------------------------
CREATE TABLE player_answers (
  id            INT       NOT NULL AUTO_INCREMENT,
  session_id    INT       NOT NULL,
  user_id       INT,
  question_id   INT,
  answer_index  SMALLINT,
  is_correct    TINYINT(1) NOT NULL DEFAULT 0,
  points_earned INT       NOT NULL DEFAULT 0,
  response_ms   INT,
  answered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_pa_session  FOREIGN KEY (session_id)  REFERENCES game_sessions(id) ON DELETE CASCADE,
  CONSTRAINT fk_pa_user     FOREIGN KEY (user_id)     REFERENCES users(id),
  CONSTRAINT fk_pa_question FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- =========================================================
--  DATOS INICIALES — TEMAS
-- =========================================================
INSERT INTO topics (name, description, icon_code, color_code) VALUES
('Geografia Mundial',      'Paises, capitales, rios y montanas del mundo', 1, 1),
('Ciencia y Tecnologia',   'Fisica, quimica, biologia e informatica',       2, 2),
('Cine y Entretenimiento', 'Peliculas, musica, series y cultura popular',   3, 3);

-- =========================================================
--  PREGUNTAS TEMA 1: GEOGRAFIA
-- =========================================================
INSERT INTO questions (topic_id, question_text, answer_options, correct_answer, time_limit, difficulty_level) VALUES
(1,'Cual es el rio mas largo del mundo?','["Amazonas","Nilo","Misisipi","Yangtse"]',1,20,2),
(1,'Cual es el pais mas grande del mundo por superficie?','["Canada","China","Rusia","Estados Unidos"]',2,20,1),
(1,'Cual es la capital de Australia?','["Sydney","Melbourne","Brisbane","Canberra"]',3,20,2),
(1,'Cual es el oceano mas grande del mundo?','["Atlantico","Indico","Pacifico","Artico"]',2,20,1),
(1,'Cuantos paises tiene el continente africano?','["48","54","60","42"]',1,25,3),
(1,'Cual es la montana mas alta del mundo?','["K2","Mont Blanc","Aconcagua","Monte Everest"]',3,20,1),
(1,'Cual es el pais mas pequeno del mundo?','["Monaco","San Marino","Ciudad del Vaticano","Liechtenstein"]',2,20,2),
(1,'En que continente esta el desierto del Sahara?','["Asia","Africa","America del Sur","Australia"]',1,20,1),
(1,'Cual es el lago mas grande del mundo por superficie?','["Lago Superior","Lago Victoria","Mar Caspio","Lago Huron"]',2,25,3),
(1,'Cual es la ciudad mas poblada del mundo?','["Delhi","Ciudad de Mexico","Tokio","Shanghai"]',2,20,2),
(1,'Que pais tiene mas fronteras terrestres?','["China","Rusia","Brasil","Alemania"]',1,25,3),
(1,'Cual es la cascada mas alta del mundo?','["Cataratas del Niagara","Salto del Angel","Cataratas Victoria","Cataratas Iguazu"]',1,20,2);

-- =========================================================
--  PREGUNTAS TEMA 2: CIENCIA Y TECNOLOGIA
-- =========================================================
INSERT INTO questions (topic_id, question_text, answer_options, correct_answer, time_limit, difficulty_level) VALUES
(2,'A que velocidad viaja la luz en el vacio?','["150000 km/s","300000 km/s","500000 km/s","250000 km/s"]',1,20,2),
(2,'Cuantos elementos tiene la tabla periodica actualmente?','["112","115","118","120"]',2,20,2),
(2,'Cual es el planeta mas grande del sistema solar?','["Saturno","Jupiter","Neptuno","Urano"]',1,20,1),
(2,'Cuanto tarda la luz del Sol en llegar a la Tierra?','["4 minutos","8 minutos","12 minutos","1 minuto"]',1,20,2),
(2,'Que particula subatomica tiene carga positiva?','["Electron","Neutron","Foton","Proton"]',3,20,1),
(2,'En que ano fue lanzado el primer iPhone?','["2005","2006","2007","2008"]',2,20,2),
(2,'Que significa la sigla ADN?','["Acido Desoxirribonucleico","Acido Deoxyribonico Natural","Aminoacido Desoxirribonucleico","Acido Dinucleico Natural"]',0,25,2),
(2,'Quien formulo la Teoria General de la Relatividad?','["Isaac Newton","Stephen Hawking","Albert Einstein","Nikola Tesla"]',2,20,1),
(2,'Cuantos huesos tiene el cuerpo humano adulto?','["186","206","226","196"]',1,20,2),
(2,'Cual es el elemento mas abundante en el universo?','["Oxigeno","Helio","Hidrogeno","Carbono"]',2,20,2),
(2,'Que empresa desarrollo Android?','["Apple","Microsoft","Google","Samsung"]',2,20,1),
(2,'En que ano se fundo SpaceX?','["2000","2002","2004","2006"]',1,25,3);

-- =========================================================
--  PREGUNTAS TEMA 3: CINE Y ENTRETENIMIENTO
-- =========================================================
INSERT INTO questions (topic_id, question_text, answer_options, correct_answer, time_limit, difficulty_level) VALUES
(3,'Quien dirigio la pelicula Titanic (1997)?','["Steven Spielberg","Christopher Nolan","James Cameron","Martin Scorsese"]',2,20,1),
(3,'En que ano se estreno la primera pelicula de Star Wars?','["1975","1977","1979","1981"]',1,20,2),
(3,'Que actor interpreto a Jack Sparrow en Piratas del Caribe?','["Brad Pitt","Tom Hanks","Will Smith","Johnny Depp"]',3,20,1),
(3,'Cuantas peliculas tiene la saga principal de Harry Potter?','["6","7","8","9"]',2,20,1),
(3,'Que banda compuso Bohemian Rhapsody?','["The Beatles","Led Zeppelin","Queen","Rolling Stones"]',2,20,1),
(3,'En que ano se fundo Netflix?','["1995","1997","2000","2003"]',1,20,2),
(3,'Quien creo a los personajes de Los Simpsons?','["Seth MacFarlane","Matt Groening","Trey Parker","Mike Judge"]',1,20,2),
(3,'En que pais se produce principalmente el anime?','["China","Corea del Sur","Japon","Estados Unidos"]',2,20,1),
(3,'Quien es el protagonista de El Senor de los Anillos?','["Gandalf","Aragorn","Frodo Bolson","Legolas"]',2,20,1),
(3,'En que ano se lanzo YouTube?','["2003","2004","2005","2006"]',2,20,2),
(3,'Cuantas temporadas tiene Breaking Bad?','["4","5","6","7"]',1,20,2),
(3,'Que pelicula de Pixar presenta a WALL-E?','["Ratatouille","Cars","WALL-E","Up"]',2,20,1);

-- =========================================================
--  VISTA: leaderboard
-- =========================================================
CREATE VIEW leaderboard AS
SELECT
  username,
  total_score,
  games_played,
  games_won,
  ROUND(
    CAST(games_won AS DECIMAL(10,2)) / NULLIF(games_played, 0) * 100,
    1
  ) AS win_pct
FROM users
ORDER BY total_score DESC;
