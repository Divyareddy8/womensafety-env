from app.main import app
import uvicorn

#  REQUIRED BY OPENENV
def main():
    return app

#  local dev only
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)