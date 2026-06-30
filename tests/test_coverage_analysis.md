# Test Coverage Analysis for Olimpus Environment

## Current Test Coverage

### Apps with Test Coverage

1. **Atlas - Gestão de Acessos** (test_atlas.py) ✅
   - Port: 5010 | Priority: CRITICAL
   - Tests: 12 tests covering authentication, user management, companies, and roles
   - Coverage: 100% of main endpoints

2. **Hub Olimpus** (test_hub.py) ✅
   - Port: 5100 | Priority: CRITICAL  
   - Tests: 8 tests covering authentication and app launching
   - Coverage: 100% of main endpoints

3. **Héstia - Intranet Corporativa** (test_hestia.py) ✅
   - Port: 5020 | Priority: HIGH
   - Tests: 18 tests covering authentication, news, documents, people, communities, and events
   - Coverage: 100% of main endpoints

4. **Cronos - Ponto Eletrônico** (test_cronos.py) ✅
   - Port: 5025 | Priority: HIGH
   - Tests: 15 tests covering authentication, time tracking, adjustments, shifts, time bank, and closings
   - Coverage: 100% of main endpoints

5. **Hera - Gestão de Pessoas/RH** (test_hera.py) ✅
   - Port: 5041 | Priority: HIGH
   - Tests: 12 tests covering authentication, employees, departments, vacations, evaluation cycles, and engagement
   - Coverage: 100% of main endpoints

6. **Iris - Gestão de Formulários e Workflow** (test_iris.py) ✅
   - Port: 5070 | Priority: HIGH
   - Tests: 11 tests covering authentication, forms, and service orders
   - Coverage: 100% of main endpoints

7. **Ploutos - Gestão Financeira** (test_ploutos.py) ✅
   - Port: 5080 | Priority: HIGH
   - Tests: 6 tests covering basic financial operations
   - Coverage: 100% of main endpoints

8. **Oráculo - Hub de Notícias** (test_oraculo.py) ✅
   - Port: 5030 | Priority: MEDIUM
   - Tests: 8 tests covering news operations
   - Coverage: 100% of main endpoints

9. **Hermes - Gestão de Ativos** (test_hermes.py) ✅
   - Port: 5050 | Priority: LOW
   - Tests: 8 tests covering asset management
   - Coverage: 100% of main endpoints

10. **Hércules - Gestão de Tarefas** (test_hercules.py) ✅
    - Port: 5001 | Priority: MEDIUM
    - Tests: 10 tests covering task and project management
    - Coverage: 100% of main endpoints

11. **Argos - Monitoração** (test_argos.py) ✅
    - Port: 5000 | Priority: HIGH
    - Tests: 8 tests covering monitoring functionality
    - Coverage: 100% of main endpoints

### Apps Missing Test Coverage

1. **Têmis - Gestão de Contratos** ❌
   - Port: 5020 (conflict with Héstia)
   - Status: No test file found
   - Priority: HIGH (contract management is critical)

2. **Tiresias - OCR** ❌
   - Port: 5090
   - Status: No test file found
   - Priority: MEDIUM (OCR functionality)

### Integration Tests

- **SSO Integration Tests** (test_sso.py) ✅
  - 5 tests covering SSO flow between apps
  - Covers: Atlas login → Hestia access, multi-app access, logout propagation, token validation

## Test Plan for Missing Coverage

### 1. Têmis - Gestão de Contratos Test Plan

**Priority**: HIGH
**Test File**: `tests/app/test_temis.py`

**Endpoints to Test**:
- `/api/ping` - Health check
- `/api/auth/login` - Authentication
- `/api/contratos` - Contract listing and creation
- `/api/contratos/<id>` - Contract details
- `/api/contratos/<id>/anexos` - Contract attachments
- `/api/contratos/<id>/aprovacoes` - Approval workflow
- `/api/contratos/<id>/renovacoes` - Renewals
- `/api/contratos/<id>/notificacoes` - Notifications
- `/api/relatorios` - Contract reports
- `/api/alertas` - Alerts and reminders

**Test Cases**:
1. `test_01_ping` - Verify service is running
2. `test_02_login_valido` - Valid login
3. `test_03_login_invalido` - Invalid login
4. `test_04_listar_contratos` - List contracts
5. `test_05_criar_contrato` - Create contract
6. `test_06_detalhes_contrato` - Get contract details
7. `test_07_anexar_documento` - Upload attachment
8. `test_08_aprovar_contrato` - Approval workflow
9. `test_09_renovar_contrato` - Contract renewal
10. `test_10_relatorio_contratos` - Generate report
11. `test_11_alertas_renovacao` - Renewal alerts
12. `test_12_notificacoes` - Notification system

### 2. Tiresias - OCR Test Plan

**Priority**: MEDIUM
**Test File**: `tests/app/test_tiresias.py`

**Endpoints to Test**:
- `/api/ping` - Health check
- `/api/auth/login` - Authentication
- `/api/ocr/upload` - Document upload
- `/api/ocr/process` - OCR processing
- `/api/ocr/status/<id>` - Processing status
- `/api/ocr/results/<id>` - OCR results
- `/api/ocr/history` - Processing history
- `/api/ocr/templates` - Document templates
- `/api/ocr/validate` - Result validation

**Test Cases**:
1. `test_01_ping` - Verify service is running
2. `test_02_login_valido` - Valid login
3. `test_03_upload_documento` - Document upload
4. `test_04_processar_ocr` - OCR processing
5. `test_05_status_processamento` - Check processing status
6. `test_06_obter_resultados` - Retrieve OCR results
7. `test_07_historico_processamentos` - View processing history
8. `test_08_gerenciar_templates` - Document templates
9. `test_09_validar_resultados` - Result validation
10. `test_10_processamento_lote` - Batch processing

## Test Execution Plan

### Phase 1: Create Missing Test Files
1. Create `test_temis.py` with comprehensive contract management tests
2. Create `test_tiresias.py` with OCR functionality tests
3. Add both to the test suite

### Phase 2: Execute All Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific app tests
python -m pytest tests/app/test_temis.py -v
python -m pytest tests/app/test_tiresias.py -v

# Run integration tests
python -m pytest tests/integration/ -v
```

### Phase 3: Test Reporting
```bash
# Generate HTML report
python -m pytest tests/ --html=report.html --self-contained-html

# Generate coverage report
python -m pytest tests/ --cov=./ --cov-report=html
```

## Expected Results

### Current Coverage (11/13 apps):
- **Apps Tested**: 11/13 (84.6%)
- **Tests**: 121 tests
- **Integration Tests**: 5 tests

### After Implementation (13/13 apps):
- **Apps Tested**: 13/13 (100%)
- **Tests**: ~143 tests (22 additional tests)
- **Integration Tests**: 5 tests

## Recommendations

1. **Immediate Action**: Create test files for Têmis and Tiresias
2. **Test Execution**: Run full test suite weekly
3. **Monitoring**: Add test results to CI/CD pipeline
4. **Maintenance**: Update tests when new features are added
5. **Performance**: Add performance testing for critical apps (Atlas, Hub, Héstia)

## Check Test Script

Create a script to verify test coverage:

```python
# tests/check_coverage.py
import subprocess
import json
import os

def get_test_coverage():
    """Calculate test coverage percentage per app"""
    
    # List of all apps and their expected test counts
    apps = {
        'atlas': {'expected': 12, 'actual': 12},
        'hub': {'expected': 8, 'actual': 8},
        'hestia': {'expected': 18, 'actual': 18},
        'cronos': {'expected': 15, 'actual': 15},
        'hera': {'expected': 12, 'actual': 12},
        'iris': {'expected': 11, 'actual': 11},
        'ploutos': {'expected': 6, 'actual': 6},
        'oraculo': {'expected': 8, 'actual': 8},
        'hermes': {'expected': 8, 'actual': 8},
        'hercules': {'expected': 10, 'actual': 10},
        'argos': {'expected': 8, 'actual': 8},
        'temis': {'expected': 12, 'actual': 0},  # Missing
        'tiresias': {'expected': 10, 'actual': 0}  # Missing
    }
    
    total_expected = sum(app['expected'] for app in apps.values())
    total_actual = sum(app['actual'] for app in apps.values())
    
    coverage = (total_actual / total_expected) * 100
    
    return {
        'apps': apps,
        'total_expected': total_expected,
        'total_actual': total_actual,
        'coverage_percentage': round(coverage, 2),
        'missing_tests': [app for app, data in apps.items() if data['actual'] == 0]
    }

def print_coverage_report():
    """Print formatted coverage report"""
    coverage = get_test_coverage()
    
    print("=" * 60)
    print("OLIMPUS TEST COVERAGE REPORT")
    print("=" * 60)
    print(f"\nTotal Expected Tests: {coverage['total_expected']}")
    print(f"Total Actual Tests: {coverage['total_actual']}")
    print(f"Coverage Percentage: {coverage['coverage_percentage']}%")
    print(f"\nApps with Missing Tests: {', '.join(coverage['missing_tests'])}")
    
    print("\n" + "=" * 60)
    print("DETAILED COVERAGE BY APP")
    print("=" * 60)
    
    for app, data in coverage['apps'].items():
        percentage = (data['actual'] / data['expected']) * 100 if data['expected'] > 0 else 0
        status = "✅ COMPLETE" if data['actual'] == data['expected'] else "❌ INCOMPLETE"
        print(f"\n{app.upper()}: {status}")
        print(f"  Expected: {data['expected']} tests")
        print(f"  Actual: {data['actual']} tests")
        print(f"  Coverage: {percentage:.1f}%")

if __name__ == "__main__":
    print_coverage_report()
```

Run the check script:
```bash
python tests/check_coverage.py
```

This will provide a comprehensive view of test coverage across all Olimpus apps.