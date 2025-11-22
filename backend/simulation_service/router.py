from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from database import get_db
import models
from user_service.auth import get_current_user

router = APIRouter()

@router.get("/")
def get_simulations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    simulations = db.query(models.Simulation).filter(
        models.Simulation.user_id == current_user.id
    ).order_by(models.Simulation.created_at.desc()).all()
    
    return [
        {
            "id": sim.id,
            "name": sim.name,
            "start_date": sim.start_date,
            "end_date": sim.end_date,
            "initial_capital": float(sim.initial_capital),
            "final_capital": float(sim.final_capital) if sim.final_capital else None,
            "roi": float(sim.roi) if sim.roi else None,
            "status": sim.status,
            "created_at": sim.created_at
        }
        for sim in simulations
    ]

@router.post("/run")
def run_simulation(
    strategy_config: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    simulation = models.Simulation(
        user_id=current_user.id,
        name=strategy_config.get("name", "Simulation"),
        strategy_config=strategy_config,
        start_date=datetime.strptime(strategy_config["start_date"], "%Y-%m-%d").date(),
        end_date=datetime.strptime(strategy_config["end_date"], "%Y-%m-%d").date(),
        initial_capital=strategy_config.get("initial_capital", 10000000),
        status="running"
    )
    db.add(simulation)
    db.commit()
    
    return {"message": "Simulation started", "simulation_id": simulation.id}