"""
One-time setup script to download classifier models and pre-populate database with data neccessary for fact extraction.
"""

from sqlalchemy import create_engine, desc
from idetect.model import db_url, Base, Analysis, Session, Status, Document, DocumentType
import csv

# connect to the DB specified in the docker.env file
engine = create_engine(db_url())
Session.configure(bind=engine)

# create the DB schema, if it doesn't already exist
Base.metadata.create_all(engine)

if __name__ == "__main__":

    session = Session()
    with open('/home/idetect/data/input_urls.csv') as f:
        c = csv.reader(f)
        i = 0
        for l in c:
            url_id, gkgrecordid, date, source_common_name, document_identifier, locations, v2_counts, v2_themes  = l
            if not document_identifier.startswith('http'):
                continue
            try:
                article = Document(legacy_id=url_id, url=document_identifier, name="New Document", type=DocumentType.WEB)
                session.add(article)
                session.commit()
            except:
                pass
            i += 1
            if i % 10 == 0:
                print("{} {}".format(i, document_identifier))
