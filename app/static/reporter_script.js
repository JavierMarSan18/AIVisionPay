

function showError(error) {
  reportDetails.innerHTML = `
      <div class="empty-state">
        <div>⚠️</div>
        <p>Error al cargar el reporte</p>
        <p><small>${error.message || 'Error desconocido'}</small></p>
      </div>
    `;
  console.error('Error:', error);
}

function getStatusClass(status) {
  if (status === 'OK') return 'status-success';
  if (status === 'WARNING') return 'status-warning';
  if (status === 'ERROR') return 'status-danger';
  return '';
}

document.addEventListener('DOMContentLoaded', function () {
  const versionList = document.getElementById('version-list');
  const reportList = document.getElementById('report-list');
  const reportDetails = document.getElementById('report-details');
  const searchInput = document.getElementById('search-class');
  const clearSearchBtn = document.getElementById('clear-search');
  const statusFilter = document.getElementById('status-filter');
  const sizeFilter = document.getElementById('size-filter');
  const sortBy = document.getElementById('sort-by');
  const summaryStats = document.getElementById('summary-stats');

  let currentData = [];
  let scrollPosition = 0;
  let currentReportContainer = document.querySelector('.panel:last-child');

  function saveScrollPosition() {
    scrollPosition = currentReportContainer.scrollTop;
  }

  function restoreScrollPosition() {
    if (scrollPosition > 0) {
      currentReportContainer.scrollTop = scrollPosition;
    }
  }

  function showFiles(version, files) {
    saveScrollPosition();

    reportList.innerHTML = '';
    reportDetails.innerHTML = '<div class="loading">Cargando...</div>';
    summaryStats.innerHTML = '';

    document.querySelectorAll('#version-list .btn').forEach(btn => {
      btn.classList.remove('active');
    });

    document.querySelectorAll('#version-list .btn').forEach(btn => {
      if (btn.textContent === version) {
        btn.classList.add('active');
      }
    });

    files.sort((a, b) => b.localeCompare(a));

    if (files.length === 0) {
      reportList.innerHTML = '<div class="empty-state">No hay archivos de reporte para esta versión</div>';
      reportDetails.innerHTML = '<div class="empty-state">No hay datos para mostrar</div>';
      return;
    }

    files.forEach(file => {
      const btn = document.createElement('button');
      btn.className = 'btn';
      btn.textContent = file;
      btn.onclick = () => {
        saveScrollPosition();
        loadReportDetails(version, file);
      };
      reportList.appendChild(btn);
    });

    restoreScrollPosition();
  }

  function loadReportDetails(version, file) {
    saveScrollPosition();

    document.querySelectorAll('#report-list .btn').forEach(btn => {
      btn.classList.remove('active');
    });

    document.querySelectorAll('#report-list .btn').forEach(btn => {
      if (btn.textContent === file) {
        btn.classList.add('active');
      }
    });

    reportDetails.innerHTML = '<div class="loading">Cargando detalles del reporte...</div>';
    summaryStats.innerHTML = '';

    fetch(`/reports/${version}/${file}`)
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        currentData = data;
        applyFilters();
        restoreScrollPosition();
      })
      .catch(error => {
        showError(error);
        restoreScrollPosition();
      });
  }


  function applyFilters() {
    if (!currentData || currentData.length === 0) {
      reportDetails.innerHTML = '<div class="empty-state">No hay datos en este reporte</div>';
      return;
    }


    let filteredData = [...currentData];


    const searchTerm = searchInput.value.toLowerCase();
    if (searchTerm) {
      filteredData = filteredData.filter(entry =>
        entry.class.toLowerCase().includes(searchTerm)
      );
    }


    const statusValue = statusFilter.value;
    if (statusValue !== 'all') {
      filteredData = filteredData.filter(entry =>
        entry.train_status === statusValue || entry.validation_status === statusValue
      );
    }


    const sizeValue = sizeFilter.value;
    if (sizeValue !== 'all') {
      filteredData = filteredData.filter(entry => {
        const total = entry.train_count + entry.validation_count;
        switch (sizeValue) {
          case 'small': return total < 500;
          case 'medium': return total >= 500 && total <= 2000;
          case 'large': return total > 2000;
          default: return true;
        }
      });
    }


    const sortValue = sortBy.value;
    filteredData.sort((a, b) => {
      const totalA = a.train_count + a.validation_count;
      const totalB = b.train_count + b.validation_count;

      switch (sortValue) {
        case 'name-asc': return a.class.localeCompare(b.class);
        case 'name-desc': return b.class.localeCompare(a.class);
        case 'count-asc': return totalA - totalB;
        case 'count-desc': return totalB - totalA;
        default: return 0;
      }
    });


    displayReportDetails(filteredData);
    updateSummaryStats(filteredData);
  }


  function displayReportDetails(data) {
    if (!data || data.length === 0) {
      reportDetails.innerHTML = '<div class="empty-state">No hay resultados que coincidan con los filtros</div>';
      return;
    }

    let html = '';

    data.forEach(entry => {
      const trainStatusClass = getStatusClass(entry.train_status);
      const validationStatusClass = getStatusClass(entry.validation_status);
      const totalCount = entry.train_count + entry.validation_count;

      html += `
        <div class="report-entry">
          <h3>${entry.class}</h3>
          <div class="data-row">
            <span class="data-label">Total muestras:</span>
            <span>${totalCount}</span>
          </div>
          <div class="data-row">
            <span class="data-label">Entrenamiento:</span>
            <span>${entry.train_count} <span class="status ${trainStatusClass}">${entry.train_status}</span></span>
          </div>
          <div class="data-row">
            <span class="data-label">Validación:</span>
            <span>${entry.validation_count} <span class="status ${validationStatusClass}">${entry.validation_status}</span></span>
          </div>
        </div>
      `;
    });

    reportDetails.innerHTML = html;
  }


  function updateSummaryStats(data) {
    if (!data || data.length === 0) return;

    const totalClasses = data.length;
    let okCount = 0;
    let warningCount = 0;
    let errorCount = 0;
    let totalSamples = 0;

    data.forEach(entry => {
      totalSamples += entry.train_count + entry.validation_count;
      if (entry.train_status === 'OK' && entry.validation_status === 'OK') {
        okCount++;
      } else if (entry.train_status === 'ERROR' || entry.validation_status === 'ERROR') {
        errorCount++;
      } else {
        warningCount++;
      }
    });

    const avgSamples = Math.round(totalSamples / totalClasses);

    summaryStats.innerHTML = `
      <div class="stat-item">Total clases: <span class="stat-value">${totalClasses}</span></div>
      <div class="stat-item">Total muestras: <span class="stat-value">${totalSamples}</span></div>
      <div class="stat-item">Promedio/clase: <span class="stat-value">${avgSamples}</span></div>
      <div class="stat-item"><span class="status status-success">OK</span>: <span class="stat-value">${okCount}</span></div>
      <div class="stat-item"><span class="status status-warning">WARNING</span>: <span class="stat-value">${warningCount}</span></div>
      <div class="stat-item"><span class="status status-danger">ERROR</span>: <span class="stat-value">${errorCount}</span></div>
    `;
  }




  searchInput.addEventListener('input', applyFilters);
  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    applyFilters();
  });
  statusFilter.addEventListener('change', applyFilters);
  sizeFilter.addEventListener('change', applyFilters);
  sortBy.addEventListener('change', applyFilters);


  fetch("/reports/index.json")
    .then(res => {
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      return res.json();
    })
    .then(indexData => {
      Object.keys(indexData).forEach(ver => {
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.textContent = ver;
        btn.onclick = () => showFiles(ver, indexData[ver]);
        versionList.appendChild(btn);
      });

      const versions = Object.keys(indexData);
      if (versions.length > 0) {
        showFiles(versions[0], indexData[versions[0]]);
      }
    })
    .catch(error => {
      versionList.innerHTML = '<div class="empty-state">Error al cargar las versiones</div>';
      console.error('Error al cargar el índice:', error);
    });
});