document.addEventListener('DOMContentLoaded', () => {
    hideDrawingIfMissing();
    fetchData();
});

// Hides the drawing section if latest_setup_drawing.svg cannot be loaded.
function hideDrawingIfMissing() {
    const drawing = document.getElementById('setup-drawing');
    const hide = () => {
        document.getElementById('drawing-info').style.display = 'none';
    };
    drawing.addEventListener('error', hide);
    if (drawing.complete && drawing.naturalWidth === 0) {
        hide();
    }
}

async function fetchData() {
    try {
        // Fetch the latest setup file
        const response = await fetch('latest_setup.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        renderDashboard(data);
    } catch (error) {
        console.error("Failed to load setup data:", error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'flex';
        document.getElementById('error-message').innerText = "Could not fetch the latest setup sheet. Please ensure the GitHub Action has run successfully.";
    }
}

function renderDashboard(data) {
    // Hide loading, show dashboard
    document.getElementById('loading').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'grid';

    // Update Header Date
    if (data.meta && data.meta.date) {
        const dateObj = new Date(data.meta.date);
        const formattedDate = dateObj.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        document.getElementById('setup-date').innerText = `Last Updated: ${formattedDate} (v${data.meta.version || '?'})`;
    } else {
        document.getElementById('setup-date').innerText = `Last Updated: Unknown`;
    }

    // Render Sections
    const props = data.properties || {};
    
    // 1. General Info (we can extract top level meta or general properties)
    const generalContainer = document.getElementById('general-grid');
    if (data.meta) {
        generalContainer.appendChild(createRow('Description', data.meta.description));
        generalContainer.appendChild(createRow('Top Speed (km/h)', data.meta.top_speed_kmh !== null ? data.meta.top_speed_kmh : 'N/A'));
    }

    // 2. Suspension & Geometry
    if (props.suspension_and_geometry) {
        renderSectionData('suspension-grid', props.suspension_and_geometry);
    } else {
        document.getElementById('suspension-info').style.display = 'none';
    }

    // 3. Drivetrain
    if (props.drivetrain) {
        renderSectionData('drivetrain-grid', props.drivetrain);
    } else {
        document.getElementById('drivetrain-info').style.display = 'none';
    }

    // 4. Electronics & Control
    if (props.electronics_and_control) {
        renderSectionData('electronics-grid', props.electronics_and_control);
    } else {
        document.getElementById('electronics-info').style.display = 'none';
    }
}

function renderSectionData(containerId, sectionData) {
    const container = document.getElementById(containerId);
    
    for (const [key, value] of Object.entries(sectionData)) {
        const formattedKey = formatKey(key);
        
        if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
            // Nested object
            const row = document.createElement('div');
            row.className = 'data-row';
            row.style.flexDirection = 'column';
            row.style.alignItems = 'flex-start';
            
            const label = document.createElement('span');
            label.className = 'data-label';
            label.innerText = formattedKey;
            
            const nestedGroup = document.createElement('div');
            nestedGroup.className = 'nested-group';
            nestedGroup.style.width = '100%';
            
            for (const [subKey, subValue] of Object.entries(value)) {
                nestedGroup.appendChild(createRow(formatKey(subKey), subValue));
            }
            
            row.appendChild(label);
            row.appendChild(nestedGroup);
            container.appendChild(row);
        } else {
            // Simple key-value
            container.appendChild(createRow(formattedKey, value));
        }
    }
}

function createRow(label, value) {
    const row = document.createElement('div');
    row.className = 'data-row';

    const labelSpan = document.createElement('span');
    labelSpan.className = 'data-label';
    labelSpan.innerText = label;

    const valueSpan = document.createElement('span');
    valueSpan.className = 'data-value';
    
    // Format value
    if (value === null || value === undefined) {
        valueSpan.innerText = 'N/A';
        valueSpan.style.color = 'var(--text-secondary)';
    } else if (typeof value === 'boolean') {
        valueSpan.innerText = value ? 'Yes' : 'No';
    } else {
        valueSpan.innerText = value;
    }

    row.appendChild(labelSpan);
    row.appendChild(valueSpan);
    return row;
}

function formatKey(key) {
    return key
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
