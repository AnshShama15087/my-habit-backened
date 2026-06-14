from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# =====================================================================
# LAYER 1: THE DATABASE ENGINE SETUP
# =====================================================================
# Create a local database file named 'habits.db'
DATABASE_URL = "sqlite:///./habits.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# This sessionmaker is our "factory" to create database connections
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This is the base blueprint that turns a standard Python class into a Database Table
DB_Base = declarative_base()

# Define how our Habit table looks inside the physical database
class DB_Habit_Model(DB_Base):
    __tablename__ = "habits_table"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    is_completed = Column(Boolean, default=False)

# Tell SQLAlchemy to physically create the database file and tables on our computer
DB_Base.metadata.create_all(bind=engine)


# =====================================================================
# LAYER 2: THE DATA GATEKEEPER (PYDANTIC)
# =====================================================================
class HabitBlueprint(BaseModel):
    title: str = Field(min_length=3)
    is_completed: bool = False


# =====================================================================
# LAYER 3: THE WEB ROUTER (FASTAPI)
# =====================================================================
app = FastAPI()

# A tiny helper function to handle opening and closing database sessions safely
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/add-habit")
def create_habit(incoming_data: HabitBlueprint, db: Session = Depends(get_db)):
    
    # 1. Take the clean, validated data from Pydantic and map it to our DB structure
    new_db_row = DB_Habit_Model(
        title=incoming_data.title, 
        is_completed=incoming_data.is_completed
    )
    
    # 2. Add it to our database session and save it permanently
    db.add(new_db_row)
    db.commit()
    db.refresh(new_db_row)
    
    return {"message": f"Successfully saved '{new_db_row.title}' directly into our real SQL Database with ID: {new_db_row.id}!"}


@app.get("/habits")
def get_all_habits(db: Session = Depends(get_db)):
    
    # 1. This talks to the database and fetches EVERY row in the habits_table
    all_habits = db.query(DB_Habit_Model).all()
    
    # 2. FastAPI automatically converts these database rows into clean JSON
    return all_habits


@app.delete("/habits/{habit_id}")
def delete_habit(habit_id: int, db: Session = Depends(get_db)):
    
    target_habit = db.query(DB_Habit_Model).filter(DB_Habit_Model.id == habit_id).first()

    if target_habit is None:
      raise HTTPException(status_code=404, detail="habit not found")
    
    db.delete(target_habit)
    db.commit()

    return {"message": f"Successfully deleted habit {target_habit.title} from database."}


@app.put("/habits/{habit_id}/complete")
def complete_habit(habit_id: int, db: Session = Depends(get_db)):

    habit = db.query(DB_Habit_Model).filter(DB_Habit_Model.id == habit_id).first()

    if not habit:
        return {"error": "habit not found"}
    
    habit.is_completed = not habit.is_completed

    db.commit()
    db.refresh(habit)

    return {"message": f"Habit '{habit.title}' marked as completed!", "current_status": habit.is_completed}


@app.get("/false-habits")
def get_all_false_habits(db: Session = Depends(get_db)):
    all_false_habits = db.query(DB_Habit_Model).filter(DB_Habit_Model.is_completed == False).all()
    return all_false_habits