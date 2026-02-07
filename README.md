# Jellyfin Organizer

An intelligent automation tool that scans your Jellyfin movie library and automatically suggests collections and tags based on franchises, studios, genres, formats, lengths, audiences, and moods.

## 🎯 Project Goals

- **Automate Library Organization**: Eliminate manual collection and tag creation in Jellyfin
- **Smart Detection**: Automatically identify movie franchises, sequels, and patterns
- **Multi-Dimensional Tagging**: Organize movies by studio, format, length, audience, and mood
- **Safe Operation**: Dry-run mode by default to preview suggestions before applying
- **Flexible Configuration**: Highly customizable suggestion rules and thresholds

## ✨ Features

### Intelligent Suggestion Engine

1. **Franchise Collections** (95% confidence)
   - Keyword-based franchise detection with custom rules
   - Automatic sequel pattern recognition (Part 2, II, Rocky 2, etc.)
   - Title similarity grouping

2. **Studio Tags** (95% confidence)
   - Recognizes major studios (Pixar, Studio Ghibli, Marvel, Disney, A24, DreamWorks, etc.)
   - Canonical studio name mapping
   - Configurable studio allowlist or auto-detection of top studios
   - Filters out generic distributors (Netflix, Amazon, etc.)

3. **Format Tags** (88% confidence)
   - Animation
   - Live Action
   - Documentary

4. **Length Tags** (80% confidence)
   - Short (≤75 minutes)
   - Standard (76–110 minutes)
   - Long (111–140 minutes)
   - Epic (>140 minutes)

5. **Audience Tags** (70-88% confidence)
   - Kids (G, TV-Y, TV-Y7)
   - Family (PG)
   - Teens (PG-13)
   - Adults (R, NC-17, TV-MA)
   - General (unrated/unclear)

6. **Mood & Occasion Tags** (62-80% confidence)
   - Cozy, Funny, Action, Dark, Emotional, Scary
   - Christmas, Halloween

### Additional Features

- **Web UI**: Simple interface to scan, review suggestions, and apply them
- **REST API**: Full API access for automation and integration
- **SQLite Database**: Local storage of items and suggestions
- **Dry-Run Mode**: Preview all changes before applying to Jellyfin
- **Confidence Scoring**: Each suggestion includes confidence level and reasoning
- **Scheduler Support**: Optional cron-based automatic scanning

## 🛠️ How It Works

1. **Scan**: Fetches all movies from your Jellyfin library via API
2. **Analyze**: Applies multiple algorithms to detect patterns:
   - Title parsing for franchise/sequel detection
   - Genre analysis for format classification
   - Runtime analysis for length tags
   - Official rating parsing for audience tags
   - Overview/tagline keyword matching for mood detection
3. **Suggest**: Generates suggestions with confidence scores and reasoning
4. **Review**: Present suggestions in web UI or via API
5. **Apply**: Creates collections in Jellyfin (tags are applied as collections for compatibility)

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Jellyfin server with API access
- Jellyfin API key

### Installation

#### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lbartuzi/sidecar_Jellyfin.git
   cd sidecar_Jellyfin
   ```

2. **Configure environment variables** in `docker-compose.yml`:
   ```yaml
   environment:
     JELLYFIN_URL: "http://your-jellyfin-server:8096"
     JELLYFIN_API_KEY: "your-api-key-here"
     JELLYFIN_USER_ID: "your-user-id"  # Optional
     DRY_RUN: "true"  # Start with dry-run enabled
   ```

3. **Start the container**:
   ```bash
   docker-compose up -d
   ```

4. **Access the web interface**:
   ```
   http://localhost:8088
   ```

#### Option 2: Build from Source

1. **Build the Docker image**:
   ```bash
   cd app
   docker build -t sidecar_jellyfin:latest .
   ```

2. **Run with environment variables**:
   ```bash
   docker run -d \
     -p 8088:8088 \
     -e JELLYFIN_URL="http://your-jellyfin:8096" \
     -e JELLYFIN_API_KEY="your-api-key" \
     -e DRY_RUN="true" \
     -v jellyfin_organizer_data:/data \
     sidecar_jellyfin:latest
   ```

#### Option 3: Local Python Development

1. **Install dependencies**:
   ```bash
   cd app
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export JELLYFIN_URL="http://localhost:8096"
   export JELLYFIN_API_KEY="your-api-key"
   export DRY_RUN="true"
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JELLYFIN_URL` | Jellyfin server URL | `http://jellyfin:8096` |
| `JELLYFIN_API_KEY` | Jellyfin API key | `abc123...` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JELLYFIN_USER_ID` | `""` | Specific user ID (if needed) |
| `DRY_RUN` | `true` | Prevent writing to Jellyfin |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8088` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MIN_GROUP_SIZE` | `2` | Minimum items to create a suggestion |
| `ENABLE_FRANCHISE` | `true` | Enable franchise detection |
| `ENABLE_STUDIO` | `true` | Enable studio tagging |
| `ENABLE_FORMAT` | `true` | Enable format tagging |
| `ENABLE_LENGTH` | `true` | Enable length tagging |
| `ENABLE_AUDIENCE` | `true` | Enable audience tagging |
| `ENABLE_MOOD` | `true` | Enable mood tagging |
| `TOP_STUDIOS` | `20` | Number of top studios to tag (if allowlist not set) |

### Advanced Configuration

#### Franchise Rules

Define custom franchise keywords in JSON format:

```json
{
  "Star Wars": ["star wars"],
  "James Bond": ["james bond", "007"],
  "Mission: Impossible": ["mission: impossible", "mission impossible"],
  "Harry Potter": ["harry potter"],
  "Police Academy": ["police academy"]
}
```

Set via environment variable:
```yaml
FRANCHISE_RULES_JSON: '{"Star Wars":["star wars"],"James Bond":["james bond","007"]}'
```

#### Studio Allowlist

Limit which studios get tagged:

```yaml
STUDIO_ALLOWLIST_JSON: '["Pixar","Studio Ghibli","A24","Marvel Studios","Lucasfilm","DreamWorks","Illumination","Disney Animation","Disney"]'
```

If not set, the top 20 studios (excluding generic distributors) will be automatically selected.

## 📖 Usage

### Web Interface

1. Open `http://localhost:8088` in your browser
2. Click **Scan** to analyze your library
3. Review the suggested collections/tags
4. Click **Apply** on individual suggestions to create them in Jellyfin

### API Endpoints

#### Health Check
```bash
GET /health
```
Returns service status and dry-run mode.

#### Scan Library
```bash
POST /scan
```
Scans Jellyfin library and generates suggestions.

**Response**:
```json
{
  "items": 450,
  "suggestions": 38,
  "dry_run": true
}
```

#### List Suggestions
```bash
GET /suggestions
```
Returns all current suggestions.

**Response**:
```json
[
  {
    "suggestion_id": "uuid-here",
    "suggestion_type": "collection",
    "title": "Star Wars",
    "confidence": 0.95,
    "item_ids": ["id1", "id2", "id3"],
    "reason": "matched franchise keywords",
    "applied": false,
    "applied_collection_id": null,
    "created_at": 1234567890
  }
]
```

#### Apply Suggestion
```bash
POST /apply/{suggestion_id}
```
Applies a specific suggestion to Jellyfin.

**Dry-run Response**:
```json
{
  "ok": true,
  "dry_run": true,
  "would_create_collection": "Star Wars",
  "would_add_items": 12
}
```

**Real Apply Response**:
```json
{
  "ok": true,
  "collection_id": "jellyfin-collection-id",
  "added_items": 12
}
```

## 🗂️ Project Structure

```
sidecar_Jellyfin/
├── app/
│   ├── main.py              # FastAPI application & endpoints
│   ├── suggester.py         # Suggestion algorithm logic
│   ├── jellyfin_client.py   # Jellyfin API client
│   ├── db.py                # SQLite database operations
│   ├── settings.py          # Configuration management
│   ├── web.py               # Web UI routes
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Container build instructions
├── docker-compose.yml       # Docker Compose configuration
└── LICENSE                  # MIT License
```

## 🧩 Core Functions

### `suggester.py`

- **`build_suggestions()`**: Main suggestion generation function
- **`_base_key()`**: Extracts base title from sequels (e.g., "Rocky 2" → "Rocky")
- **`_has_sequel_marker()`**: Detects sequel patterns in titles
- **`_format_tag()`**: Determines Animation/Documentary/Live Action
- **`_length_tag()`**: Categorizes by runtime
- **`_audience_tag()`**: Determines audience rating
- **`_mood_tags()`**: Analyzes overview/genres for mood/occasion tags
- **`_canon_studio()`**: Normalizes studio names

### `jellyfin_client.py`

- **`fetch_movies()`**: Retrieves all movies from Jellyfin
- **`create_collection()`**: Creates a new collection
- **`add_items_to_collection()`**: Adds items to a collection

### `db.py`

- **`upsert_item()`**: Stores/updates movie data
- **`insert_suggestion()`**: Saves a suggestion
- **`list_suggestions()`**: Retrieves all suggestions
- **`mark_applied()`**: Marks a suggestion as applied
- **`clear_suggestions()`**: Removes old suggestions

## 🔒 Security Best Practices

- Container runs as non-root user (UID 1000)
- Read-only filesystem (except `/data` and `/tmp`)
- No sensitive data in logs
- Dry-run mode enabled by default
- API key stored as environment variable only

## 📝 Tips & Recommendations

1. **Start with Dry-Run**: Always test with `DRY_RUN=true` first to preview changes
2. **Custom Franchises**: Add your own franchise rules for niche collections
3. **Studio Curation**: Use the allowlist to focus on studios you care about
4. **Minimum Group Size**: Adjust `MIN_GROUP_SIZE` to control suggestion density
5. **Review Before Applying**: Check confidence scores and reasoning before applying
6. **Disable Unwanted Categories**: Turn off specific suggestion types if not needed

## 🐛 Troubleshooting

**Connection refused to Jellyfin**:
- Verify `JELLYFIN_URL` is correct
- Ensure Jellyfin is accessible from the container
- Check firewall rules

**No suggestions generated**:
- Verify movies exist in your Jellyfin library
- Lower `MIN_GROUP_SIZE` to 1 for testing
- Check that suggestion types are enabled

**Tags not working**:
- Tags are applied as collections (Jellyfin limitation)
- All suggestions create collections, not metadata tags

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Jellyfin](https://jellyfin.org/) - Open-source media system
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [SQLite](https://www.sqlite.org/) - Embedded database

---

**Author**: lbartuzi  
**Year**: 2026
