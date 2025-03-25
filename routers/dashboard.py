from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import os
from dotenv import load_dotenv
load_dotenv()

# Initialize MongoDB client
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
meetings_collection = db["meeting"]
place_collection = db["place"]

router = APIRouter(
    prefix="/dashboard",
    tags=['Dashboard'],
    responses={404: {
        'message': "Data not found"
    }}
)

# ---- Models for response data ----

class MeetingCountResponse(BaseModel):
    total: int
    upcoming: int
    past: int
    today: int

class TimeDistributionItem(BaseModel):
    name: str
    count: int

class MeetingTimeDistribution(BaseModel):
    by_day_of_week: List[TimeDistributionItem]
    by_hour_of_day: List[TimeDistributionItem]

class VenueUsageItem(BaseModel):
    place_id: str
    place_name: str
    meeting_count: int
    
class UserEngagementItem(BaseModel):
    user_id: str
    created_meetings: int
    enrolled_meetings: int

class MeetingDurationStats(BaseModel):
    average_minutes: float
    shortest_minutes: int
    longest_minutes: int
    by_duration_range: List[TimeDistributionItem]

# ---- Dashboard Endpoints ----

@router.get("/meeting-counts")
async def get_meeting_counts():
    """
    Get counts of total, upcoming, past, and today's meetings.
    """
    try:
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
        today_end = today_start + timedelta(days=1)

        total_count = meetings_collection.count_documents({})
        upcoming_count = meetings_collection.count_documents({"start_datetime": {"$gt": now}})
        past_count = meetings_collection.count_documents({"end_datetime": {"$lt": now}})
        today_count = meetings_collection.count_documents({
            "start_datetime": {"$gte": today_start},
            "end_datetime": {"$lt": today_end}
        })

        return MeetingCountResponse(
            total=total_count,
            upcoming=upcoming_count,
            past=past_count,
            today=today_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve meeting counts: {str(e)}")

@router.get("/time-distribution")
async def get_meeting_time_distribution(days: int = 90):
    """
    Get distribution of meetings by day of week and hour of day.
    
    Args:
        days: Number of past days to include in analysis
    """
    try:
        # Get meetings from the last X days
        start_date = datetime.now() - timedelta(days=days)
        
        # Fetch relevant meetings
        cursor = meetings_collection.find({
            "start_datetime": {"$gte": start_date}
        })
        
        day_counts = Counter()
        hour_counts = Counter()
        
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Process each meeting
        for meeting in cursor:
            start_time = meeting.get("start_datetime")
            if not isinstance(start_time, datetime):
                continue
                
            # Get day of week (0 = Monday, 6 = Sunday)
            day_of_week = start_time.weekday()
            day_counts[days_of_week[day_of_week]] += 1
            
            # Get hour of day
            hour = start_time.hour
            hour_counts[f"{hour:02d}:00"] += 1
        
        # Format results
        day_distribution = [
            TimeDistributionItem(name=day, count=day_counts[day])
            for day in days_of_week
        ]
        
        hour_distribution = [
            TimeDistributionItem(name=f"{hour:02d}:00", count=hour_counts.get(f"{hour:02d}:00", 0))
            for hour in range(24)
        ]
        
        return MeetingTimeDistribution(
            by_day_of_week=day_distribution,
            by_hour_of_day=hour_distribution
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve time distribution: {str(e)}")

@router.get("/venue-usage")
async def get_venue_usage(limit: int = 10):
    """
    Get most frequently used meeting venues.
    
    Args:
        limit: Number of top venues to return
    """
    try:
        # Aggregate venue usage
        pipeline = [
            {"$group": {"_id": "$place_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        venue_usage = list(meetings_collection.aggregate(pipeline))
        
        # Get venue names for the place_ids
        result = []
        for venue in venue_usage:
            place_id = venue["_id"]
            place_info = place_collection.find_one({"_id": place_id})
            place_name = place_info.get("name", "Unknown Venue") if place_info else "Unknown Venue"
            
            result.append(VenueUsageItem(
                place_id=place_id,
                place_name=place_name,
                meeting_count=venue["count"]
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve venue usage: {str(e)}")

@router.get("/user-engagement")
async def get_user_engagement(limit: int = 10):
    """
    Get most engaged users based on meeting creation and enrollment.
    
    Args:
        limit: Number of top users to return
    """
    try:
        # Get users who created meetings
        creator_pipeline = [
            {"$group": {"_id": "$user_create", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        creators = {item["_id"]: item["count"] for item in meetings_collection.aggregate(creator_pipeline)}
        
        # Get users who enrolled in meetings
        enrolled_pipeline = [
            {"$unwind": "$enrolled_users"},
            {"$group": {"_id": "$enrolled_users", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        enrolled = {item["_id"]: item["count"] for item in meetings_collection.aggregate(enrolled_pipeline)}
        
        # Combine results
        all_users = set(list(creators.keys()) + list(enrolled.keys()))
        
        result = []
        for user_id in all_users:
            if isinstance(user_id, str):  # Skip if not a valid user ID
                result.append(UserEngagementItem(
                    user_id=user_id,
                    created_meetings=creators.get(user_id, 0),
                    enrolled_meetings=enrolled.get(user_id, 0)
                ))
        
        # Sort by total engagement (created + enrolled)
        result.sort(key=lambda x: x.created_meetings + x.enrolled_meetings, reverse=True)
        
        return result[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user engagement: {str(e)}")

@router.get("/meeting-duration")
async def get_meeting_duration_stats():
    """
    Get statistics about meeting durations.
    """
    try:
        cursor = meetings_collection.find({
            "start_datetime": {"$exists": True},
            "end_datetime": {"$exists": True}
        })
        
        duration_minutes = []
        duration_ranges = Counter()
        
        for meeting in cursor:
            start_time = meeting.get("start_datetime")
            end_time = meeting.get("end_datetime")
            
            if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
                continue
                
            if end_time < start_time:
                continue  # Skip invalid time ranges
                
            # Calculate duration in minutes
            duration = (end_time - start_time).total_seconds() / 60
            duration_minutes.append(duration)
            
            # Categorize by duration range
            if duration <= 30:
                duration_ranges["0-30 min"] += 1
            elif duration <= 60:
                duration_ranges["31-60 min"] += 1
            elif duration <= 120:
                duration_ranges["1-2 hours"] += 1
            elif duration <= 240:
                duration_ranges["2-4 hours"] += 1
            else:
                duration_ranges["4+ hours"] += 1
        
        # Calculate statistics
        if not duration_minutes:
            average = 0
            shortest = 0
            longest = 0
        else:
            average = sum(duration_minutes) / len(duration_minutes)
            shortest = int(min(duration_minutes))
            longest = int(max(duration_minutes))
        
        # Format duration range data
        range_data = [
            TimeDistributionItem(name=range_name, count=count)
            for range_name, count in duration_ranges.items()
        ]
        
        return MeetingDurationStats(
            average_minutes=round(average, 1),
            shortest_minutes=shortest,
            longest_minutes=longest,
            by_duration_range=range_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve meeting duration stats: {str(e)}")

@router.get("/upcoming-meetings")
async def get_upcoming_meetings(days: int = 7, limit: int = 10):
    """
    Get list of upcoming meetings for quick dashboard display.
    
    Args:
        days: Number of upcoming days to include
        limit: Maximum number of meetings to return
    """
    try:
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        cursor = meetings_collection.find({
            "start_datetime": {"$gte": now, "$lte": end_date}
        }).sort("start_datetime", 1).limit(limit)
        
        upcoming_meetings = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            upcoming_meetings.append(doc)
            
        return upcoming_meetings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve upcoming meetings: {str(e)}")

@router.get("/overview")
async def get_dashboard_overview():
    """
    Get a comprehensive dashboard overview with key metrics.
    Returns aggregated data from multiple endpoints for a quick summary.
    """
    try:
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
        today_end = today_start + timedelta(days=1)
        this_week_end = now + timedelta(days=7)
        
        # Meeting counts
        total_count = meetings_collection.count_documents({})
        upcoming_count = meetings_collection.count_documents({"start_datetime": {"$gt": now}})
        past_count = meetings_collection.count_documents({"end_datetime": {"$lt": now}})
        today_count = meetings_collection.count_documents({
            "start_datetime": {"$gte": today_start},
            "end_datetime": {"$lt": today_end}
        })
        
        # Get upcoming meetings this week
        upcoming_cursor = meetings_collection.find({
            "start_datetime": {"$gte": now, "$lte": this_week_end}
        }).sort("start_datetime", 1).limit(5)
        
        upcoming_meetings = []
        for doc in upcoming_cursor:
            # Extract only needed fields for a lightweight response
            upcoming_meetings.append({
                "id": str(doc["_id"]),
                "name": doc.get("name", "Untitled Meeting"),
                "start_datetime": doc.get("start_datetime"),
                "end_datetime": doc.get("end_datetime"),
                "place_id": doc.get("place_id")
            })
        
        # Get most used venues
        venue_pipeline = [
            {"$group": {"_id": "$place_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 3}
        ]
        
        top_venues = []
        for venue in meetings_collection.aggregate(venue_pipeline):
            place_id = venue["_id"]
            place_info = place_collection.find_one({"_id": place_id})
            place_name = place_info.get("name", "Unknown Venue") if place_info else "Unknown Venue"
            
            top_venues.append({
                "place_id": place_id,
                "place_name": place_name,
                "meeting_count": venue["count"]
            })
        
        # Get most active users
        user_pipeline = [
            {"$group": {"_id": "$user_create", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 3}
        ]
        
        top_users = [{"user_id": item["_id"], "meeting_count": item["count"]} 
                     for item in meetings_collection.aggregate(user_pipeline)]
        
        # Return comprehensive overview
        return {
            "meeting_stats": {
                "total": total_count,
                "upcoming": upcoming_count,
                "past": past_count,
                "today": today_count
            },
            "upcoming_meetings": upcoming_meetings,
            "top_venues": top_venues,
            "top_users": top_users,
            "last_updated": now
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard overview: {str(e)}")

@router.get("/organizer/{user_id}")
async def get_organizer_stats(user_id: str):
    """
    Get statistics for meetings organized by a specific user.
    
    Args:
        user_id: ID of the meeting organizer
    """
    try:
        now = datetime.now()
        
        # Get all meetings created by this user
        user_meetings = list(meetings_collection.find({"user_create": user_id}))
        
        if not user_meetings:
            return {
                "total_meetings": 0,
                "message": "No meetings found for this organizer"
            }
        
        # Count meetings by status
        total_count = len(user_meetings)
        upcoming_meetings = [m for m in user_meetings if m.get("start_datetime", now) > now]
        past_meetings = [m for m in user_meetings if m.get("end_datetime", now) < now]
        upcoming_count = len(upcoming_meetings)
        past_count = len(past_meetings)
        
        # Calculate average enrollment
        enrollment_counts = [len(m.get("enrolled_users", [])) for m in user_meetings]
        avg_enrollment = sum(enrollment_counts) / len(enrollment_counts) if enrollment_counts else 0
        
        # Get most popular venues used by this organizer
        venue_counter = Counter([m.get("place_id") for m in user_meetings])
        top_venues = venue_counter.most_common(3)
        
        venue_details = []
        for place_id, count in top_venues:
            if not place_id:
                continue
                
            place_info = place_collection.find_one({"_id": place_id})
            place_name = place_info.get("name", "Unknown Venue") if place_info else "Unknown Venue"
            
            venue_details.append({
                "place_id": place_id,
                "place_name": place_name,
                "meeting_count": count
            })
        
        # Calculate average meeting duration
        durations = []
        for meeting in user_meetings:
            start_time = meeting.get("start_datetime")
            end_time = meeting.get("end_datetime")
            
            if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
                continue
                
            if end_time < start_time:
                continue
                
            duration_minutes = (end_time - start_time).total_seconds() / 60
            durations.append(duration_minutes)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Get next upcoming meeting
        next_meeting = None
        if upcoming_meetings:
            upcoming_meetings.sort(key=lambda m: m.get("start_datetime", now))
            next_meeting_data = upcoming_meetings[0]
            next_meeting = {
                "id": str(next_meeting_data["_id"]),
                "name": next_meeting_data.get("name", "Untitled Meeting"),
                "start_datetime": next_meeting_data.get("start_datetime"),
                "place_id": next_meeting_data.get("place_id")
            }
        
        return {
            "organizer_id": user_id,
            "meeting_stats": {
                "total_meetings": total_count,
                "upcoming_meetings": upcoming_count,
                "past_meetings": past_count,
                "average_enrollment": round(avg_enrollment, 1),
                "average_duration_minutes": round(avg_duration, 1)
            },
            "favorite_venues": venue_details,
            "next_meeting": next_meeting,
            "last_updated": now
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve organizer stats: {str(e)}") 