const fs = require('fs');
let content = fs.readFileSync('dashboard/index.html', 'utf8');

// 1. Add nav-staff
content = content.replace(
  '<div class="nav-section-title">Konfigurasi</div>',
  '<div class="nav-section-title">Manajemen</div>\n      <a class="nav-item" onclick="showPage(\'staff\')" id="nav-staff">\n        <span class="nav-icon">👥</span> Akun Staf\n      </a>\n\n      <div class="nav-section-title">Konfigurasi</div>'
);

// 2. Hide nav-staff for staff role
content = content.replace(
  "if (document.getElementById('nav-alerts')) document.getElementById('nav-alerts').style.display = 'none';",
  "if (document.getElementById('nav-alerts')) document.getElementById('nav-alerts').style.display = 'none';\n        if (document.getElementById('nav-staff')) document.getElementById('nav-staff').style.display = 'none';"
);

// 3. Add page-staff
const pageStaffHTML = `
    <!-- ===== STAFF MANAGEMENT PAGE ===== -->
    <div class="page" id="page-staff">
      <div class="topbar">
        <div class="page-title">👥 Manajemen Staf</div>
        <button class="btn btn-primary" onclick="openStaffModal()">+ Tambah Akun Staf</button>
      </div>
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody id="staffTable">
              <tr>
                <td>admin</td>
                <td><span class="badge-pass">Admin</span></td>
                <td>-</td>
              </tr>
              <tr>
                <td>staff</td>
                <td><span class="badge-pending">Staff</span></td>
                <td>
                  <button class="btn btn-danger btn-sm" onclick="if(confirm('Hapus akun staff?')){this.parentElement.parentElement.remove();toast('Akun staff dihapus','success')}">Hapus</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
`;
content = content.replace('<!-- ===== PRODUCTS PAGE ===== -->', pageStaffHTML + '\n    <!-- ===== PRODUCTS PAGE ===== -->');

// 4. Enhance Products page
const productsPageHTML = `    <!-- ===== PRODUCTS PAGE ===== -->
    <div class="page" id="page-products">
      <div class="topbar">
        <div class="page-title">🍱 Produk & SOP Threshold</div>
        <button class="btn btn-primary" onclick="openProductModal()">+ Tambah Produk</button>
      </div>
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Kode</th>
                <th>Nama Produk</th>
                <th>pH Range</th>
                <th>Brix Range</th>
                <th>Core Temp Min</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody id="productTable">
              <tr>
                <td>SKU-SOUP-001</td>
                <td>Tom Yam Soup Base</td>
                <td>5.5 - 6.5</td>
                <td>8.0 - 12.0</td>
                <td>75.0°C</td>
                <td>
                  <button class="btn btn-sm" onclick="alert('Edit Produk')">Edit</button>
                  <button class="btn btn-danger btn-sm" onclick="if(confirm('Hapus produk?')){this.parentElement.parentElement.remove();toast('Produk dihapus','success')}">Hapus</button>
                </td>
              </tr>
              <tr>
                <td>SKU-SAUCE-002</td>
                <td>Sweet Chili Sauce</td>
                <td>3.5 - 4.5</td>
                <td>35.0 - 45.0</td>
                <td>75.0°C</td>
                <td>
                  <button class="btn btn-sm" onclick="alert('Edit Produk')">Edit</button>
                  <button class="btn btn-danger btn-sm" onclick="if(confirm('Hapus produk?')){this.parentElement.parentElement.remove();toast('Produk dihapus','success')}">Hapus</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>`;

content = content.replace(/<!-- ===== PRODUCTS PAGE ===== -->[\s\S]*?(?=<\/main>)/, productsPageHTML + '\n\n  ');

// 5. Add Modals for Staff and Products
const modalsHTML = `
  <!-- ===== MODAL: Tambah Akun Staf ===== -->
  <div class="modal-overlay" id="staffModal">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">👥 Tambah Akun Staf</div>
        <div class="modal-close" onclick="closeModal('staffModal')">×</div>
      </div>
      <div class="form-grid">
        <div class="form-group full">
          <label>Username *</label>
          <input id="staffUsername" type="text" placeholder="Masukkan username" />
        </div>
        <div class="form-group full">
          <label>Password *</label>
          <input id="staffPassword" type="password" placeholder="Masukkan password" />
        </div>
      </div>
      <div class="modal-footer" style="margin-top:20px;display:flex;justify-content:flex-end;gap:10px">
        <button class="btn btn-ghost" onclick="closeModal('staffModal')">Batal</button>
        <button class="btn btn-primary" onclick="addStaff()">Simpan Akun</button>
      </div>
    </div>
  </div>

  <!-- ===== MODAL: Tambah/Edit Produk ===== -->
  <div class="modal-overlay" id="productModal">
    <div class="modal">
      <div class="modal-header">
        <div class="modal-title">🍱 Tambah Produk & SOP</div>
        <div class="modal-close" onclick="closeModal('productModal')">×</div>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label>Kode Produk *</label>
          <input id="prodCode" type="text" placeholder="Contoh: SKU-NEW-001" />
        </div>
        <div class="form-group">
          <label>Nama Produk *</label>
          <input id="prodName" type="text" placeholder="Contoh: Saus Teriyaki" />
        </div>
        <div class="form-group">
          <label>pH Min</label>
          <input id="prodPhMin" type="number" step="0.1" />
        </div>
        <div class="form-group">
          <label>pH Max</label>
          <input id="prodPhMax" type="number" step="0.1" />
        </div>
        <div class="form-group">
          <label>Brix Min</label>
          <input id="prodBrixMin" type="number" step="0.1" />
        </div>
        <div class="form-group">
          <label>Brix Max</label>
          <input id="prodBrixMax" type="number" step="0.1" />
        </div>
        <div class="form-group full">
          <label>Core Temp Min (°C) (Suhu Inti Matang)</label>
          <input id="prodCoreTemp" type="number" step="0.1" value="75.0" />
        </div>
      </div>
      <div class="modal-footer" style="margin-top:20px;display:flex;justify-content:flex-end;gap:10px">
        <button class="btn btn-ghost" onclick="closeModal('productModal')">Batal</button>
        <button class="btn btn-primary" onclick="saveProduct()">Simpan Produk</button>
      </div>
    </div>
  </div>
`;

content = content.replace('<!-- ===== MODAL: Input Suhu Fasilitas ===== -->', modalsHTML + '\n\n  <!-- ===== MODAL: Input Suhu Fasilitas ===== -->');

// 6. Add JS Functions for Staff and Products
const scriptHTML = `
    function openStaffModal() {
      document.getElementById('staffUsername').value = '';
      document.getElementById('staffPassword').value = '';
      document.getElementById('staffModal').classList.add('open');
    }
    function addStaff() {
      const uname = document.getElementById('staffUsername').value;
      if(!uname) { toast('Username wajib diisi', 'error'); return; }
      
      const tr = document.createElement('tr');
      tr.innerHTML = \`
        <td>\${uname}</td>
        <td><span class="badge-pending">Staff</span></td>
        <td><button class="btn btn-danger btn-sm" onclick="if(confirm('Hapus akun staff?')){this.parentElement.parentElement.remove();toast('Akun staff dihapus','success')}">Hapus</button></td>
      \`;
      document.getElementById('staffTable').appendChild(tr);
      closeModal('staffModal');
      toast('Akun staff ' + uname + ' berhasil ditambahkan', 'success');
    }

    function openProductModal() {
      document.getElementById('prodCode').value = '';
      document.getElementById('prodName').value = '';
      document.getElementById('prodPhMin').value = '';
      document.getElementById('prodPhMax').value = '';
      document.getElementById('prodBrixMin').value = '';
      document.getElementById('prodBrixMax').value = '';
      document.getElementById('prodCoreTemp').value = '75.0';
      document.getElementById('productModal').classList.add('open');
    }
    function saveProduct() {
      const code = document.getElementById('prodCode').value;
      const name = document.getElementById('prodName').value;
      if(!code || !name) { toast('Kode dan Nama Produk wajib diisi', 'error'); return; }
      
      const phMin = document.getElementById('prodPhMin').value || '-';
      const phMax = document.getElementById('prodPhMax').value || '-';
      const brixMin = document.getElementById('prodBrixMin').value || '-';
      const brixMax = document.getElementById('prodBrixMax').value || '-';
      const coreTemp = document.getElementById('prodCoreTemp').value || '75';

      const tr = document.createElement('tr');
      tr.innerHTML = \`
        <td>\${code}</td>
        <td>\${name}</td>
        <td>\${phMin} - \${phMax}</td>
        <td>\${brixMin} - \${brixMax}</td>
        <td>\${coreTemp}°C</td>
        <td>
          <button class="btn btn-sm" onclick="alert('Edit Produk')">Edit</button>
          <button class="btn btn-danger btn-sm" onclick="if(confirm('Hapus produk?')){this.parentElement.parentElement.remove();toast('Produk dihapus','success')}">Hapus</button>
        </td>
      \`;
      document.getElementById('productTable').appendChild(tr);
      closeModal('productModal');
      toast('Produk ' + name + ' berhasil ditambahkan', 'success');
    }
`;
content = content.replace('// ============================================================', scriptHTML + '\n    // ============================================================');

fs.writeFileSync('dashboard/index.html', content);
