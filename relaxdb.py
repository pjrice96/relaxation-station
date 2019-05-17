from __future__ import print_function
import os
import psycopg2

BUILD_DB = (
    """
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
      user_id SERIAL PRIMARY KEY,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS videos (
        video_id SERIAL PRIMARY KEY,
        video_name VARCHAR(255) NOT NULL,
        video_url TEXT NOT NULL,
        video_flags TEXT
    )
    """,
    """ CREATE TABLE IF NOT EXISTS user_video_map (
            user_id INTEGER NOT NULL,
            video_id INTEGER NOT NULL,
            PRIMARY KEY (user_id , video_id),
            video_tags TEXT,
            FOREIGN KEY (user_id)
                REFERENCES users (user_id)
                ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (video_id)
                REFERENCES videos (video_id)
                ON UPDATE CASCADE ON DELETE CASCADE
            )
    """ )
# USER CRUD
ADD_USER = """
    INSERT INTO users (name, email, password) VALUES (
      '{name}',
      '{email}',
      crypt('{password}', gen_salt('bf'))
    ) RETURNING user_id;
    """
CHECK_USER = """
    SELECT user_id
      FROM users
     WHERE email = '{email}'
       AND password = crypt('{password}', password);
    """
IS_USER = """
    SELECT user_id
      FROM users
     WHERE email = '{email}';
    """
RESET_PASSWORD = """
    UPDATE users
      SET password = crypt('{password}', gen_salt('bf'))
      WHERE email = '{email}';
    """
GET_ALL_USERS = """
    SELECT *
      FROM users;
    """
GET_USER_NAME = """
    SELECT name
      FROM users
      WHERE user_id={user_id};
    """
DELETE_USER_ID = """
    DELETE
      FROM users
      WHERE user_id={user_id};
    """
DELETE_USER_EMAIL = """
    DELETE
      FROM users
      WHERE email='{email}';
    """
# VIDEO CRUD
ADD_VIDEO = """
    INSERT INTO videos (video_name, video_url) VALUES (
      '{video_name}',
      '{video_url}'
    ) RETURNING video_id;
    """
GET_ALL_VIDEOS = """
    SELECT  *
      FROM videos;
    """
GET_VIDEO_ID = """
    SELECT *
      FROM videos
      WHERE video_id={video_id};
    """
DELETE_VIDEO_ID = """
    DELETE
      FROM video
      WHERE video_id={video_id};
    """
# MAP CRUD
MAP_VIDEO = """
    INSERT INTO user_video_map (video_id,user_id,video_tags) VALUES (
      {video_id},
      {user_id},
      '{video_tags}'
    );
    """
GET_MAPPED_VIDEOS = """
    SELECT videos.video_id, videos.video_name, videos.video_url, user_video_map.video_tags
      FROM videos
      INNER JOIN user_video_map ON videos.video_id=user_video_map.video_id WHERE user_video_map.user_id={user_id};
    """
GET_MAPPED_TAGS = """
    SELECT video_tags
      WHERE user_id={user_id} AND video_id={video_id};
    """
UPDATE_MAP_TAGS = """
    UPDATE user_video_map
      SET video_tags='{video_tags}'
      WHERE user_id={user_id} AND video_id={video_id};
    """
DELETE_MAP_USER_VIDEO_ID = """
    DELETE
      FROM user_video_map
      WHERE user_id={user_id} AND video_id={video_id};
    """

class RelaxDB():
    def __init__(self):
        self.DATABASE_URL = os.getenv('DATABASE_URL')
        self.dbname = 'relaxation-station'
        self.user='postgres'
        self.password='mysecretpassword'
        self.is_open_flag = False
        self.conn = None
        
        
        
    def open(self):
    
        self.conn = psycopg2.connect(self.DATABASE_URL, sslmode='require')
        self.cur = self.conn.cursor()
        self.is_open_flag = True

    def close(self):
        try:
            self.cur.close()
            # commit the changes
            self.conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
        finally:
            if self.conn is not None:
                self.conn.close()
            self.is_open_flag = False

    def is_open(self):
        return(self.is_open_flag)

    def build_db(self):
        if self.is_open():
            for command in BUILD_DB:
                try:
                    self.cur.execute(command)
                except (Exception, psycopg2.DatabaseError) as error:
                    print(error)
                    return(False)
            return(True)
        else:
            print("ERROR: Trying to build_db before connection is open to DB")
            return(False)

    def _get_rows(self,select):
        try:
            self.cur.execute(select)
            row = self.cur.fetchall()
            return(row)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def _get_one(self,select):
        try:
            self.cur.execute(select)
            row = self.cur.fetchone()
            return(row[0])
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    # USER CRUD - Create, Read, Update, Destroy
    def add_user(self,name,email,password):
        print("add_user",name,email)
        try:
            self.cur.execute(ADD_USER.format(name=name, email=email,password=password))
            row = self.cur.fetchone()
            user_id = row[0]
            return(user_id)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def is_user(self,email):
        print("is_user",email)
        try:
            self.cur.execute(IS_USER.format(email=email))
            row = self.cur.fetchone()
            #print("is_user", row)
            if row is not None:
                return(True)
            else:
                return(False)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def reset_password(self,email,password):
        print("reset_password",email)
        try:
            self.cur.execute(RESET_PASSWORD.format(email=email,password=password))
            return(True)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def check_user(self,email,password):
        print("check_user",email)
        try:
            self.cur.execute(CHECK_USER.format(email=email,password=password))
            row = self.cur.fetchone()
            print("Check_user",row)
            if row is not None:
                return(row[0])
            else:
                return(False)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def get_user_name(self, user_id):
        return(self._get_one(GET_USER_NAME.format(user_id=user_id)))

    def get_all_users(self):
        return(self._get_rows(GET_ALL_USERS))

    def delete_user_id(self,user_id):
        try:
            self.cur.execute(DELETE_USER_ID.format(user_id=user_id))
            return(True)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def delete_user_email(self,email):
        try:
            self.cur.execute(DELETE_USER_EMAIL.format(email=email))
            return(True)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    # VIDEO CRUD
    def add_video(self, video_name, video_url):
        try:
            self.cur.execute(ADD_VIDEO.format(video_name=video_name, video_url=video_url))
            row = self.cur.fetchone()
            video_id = row[0]
            return(video_id)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def get_all_videos(self):
        return(self._get_rows(GET_ALL_VIDEOS))

    def get_video_id(self,video_id):
        return(self._get_rows(GET_VIDEO_ID.format(video_id=video_id)))

    def delete_video_id(self,video_id):
        try:
            self.cur.execute(DELETE_VIDEO_ID.format(video_id=video_id))
            return(True)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    # MAP CRUD
    def map_video(self,user_id,video_id,video_tags):
        try:
            self.cur.execute(MAP_VIDEO.format(video_id=video_id, user_id=user_id, video_tags=video_tags))
            return(True)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def get_mapped_videos(self,user_id):
        return(self._get_rows(GET_MAPPED_VIDEOS.format(user_id=user_id)))

    def get_mapped_tags(self,user_id,video_id):
        return(self._get_one(GET_MAPPED_TAGS.format(user_id=user_id,video_id=video_id)))

    def update_map_tags(self,user_id,video_id,video_tags):
        try:
            self.cur.execute(UPDATE_MAP_TAGS.format(video_id=video_id, user_id=user_id, video_tags=video_tags))
            return(True)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)

    def delete_map_user_video_id(self,user_id,video_id):
        try:
            self.cur.execute(DELETE_MAP_USER_VIDEO_ID.format(user_id=user_id,video_id=video_id))
            return(True)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            return(False)


def testing():
    """ create tables in the PostgreSQL database"""

    relaxdb = RelaxDB()
    relaxdb.open()
    relaxdb.build_db()

    # Given this information from registration for
    name = 'johnDoe'
    email = 'johnDoev12345@yahoo.com'
    password = 'STREAM_WADERS'
    # Attempt to register
    if not relaxdb.is_user('johnDoev12345@yahoo.com'):
        # if email isn't registered, register user name, email and password
        relaxdb.add_user(name,email,password)
    else:
        print("Email",email,"has been used before. You may want to recover the password")

    # Given
    email = 'johnDoev12345@yahoo.com'
    password = 'STREAM_WADERS'
    # Check to see if this is valid for signing in
    if relaxdb.check_user(email,password):
        id = relaxdb.check_user(email,password)
        print("Found user",id)
    else:
        print("Invalid email or password")

    # Reset the password
    relaxdb.reset_password('johnDoev1234@yahoo.com','Balanced_Diver')

    print(relaxdb.check_user('johnDoev1234@yahoo.com','Balanced_Diver'))

    for j in range(0):
        relaxdb.add_video("video_name" + str(j), "video_url" + str(j))

    for k in range(0):
        relaxdb.add_user("johnDoe" + str(k), "email" + str(k),"password" + str(k))

    rows = relaxdb.get_all_videos()
    for id,name,url in rows:
        print(id)

    rows = relaxdb.get_all_users()
    for id,name,email,password in rows:
        print(id,name,email)


    #relaxdb.map_video(22,93,"aweful,tender")
    #relaxdb.map_video(22,92,"sadly,tender")
    #relaxdb.map_video(22,94,"terribly,tender")

    rows = relaxdb.get_mapped_videos(22)
    for id,name,url,tags in rows:
        print(id,name,url)

    relaxdb.close()



if __name__ == '__main__':
    testing()
