# Error Prevention #44: E2E 테스트 사용

## 원칙
E2E 테스트로 반복 작업을 자동화하고 실제 사용자 워크플로우가 작동하는지 확인하세요.

## E2E vs Unit Test

### Unit Test
```python
def test_calculate_total():
    assert calculate_total([10, 20]) == 30
```

### E2E Test
```python
def test_checkout_flow():
    # 1. 로그인
    login("user@example.com", "password")

    # 2. 상품 장바구니 추가
    add_to_cart("product-123")
    add_to_cart("product-456")

    # 3. 체크아웃
    checkout()

    # 4. 결제
    payment = pay_with_card("4242...")

    # 5. 검증
    assert payment.status == "success"
    assert order.total == 50.00
```

## 도구

### Web
```javascript
// Playwright
test('user can checkout', async ({ page }) => {
  await page.goto('/');
  await page.click('text=Login');
  await page.fill('#email', 'user@example.com');
  // ...
});
```

### API
```python
# pytest
def test_api_workflow():
    # Register
    resp = client.post('/auth/register', json={...})
    token = resp.json()['token']

    # Create resource
    resp = client.post('/items',
        json={...},
        headers={'Authorization': f'Bearer {token}'})
    # ...
```

## 언제 사용?
- 중요한 사용자 플로우
- 회귀 테스트
- 배포 전 검증
- 통합 확인

## 관련 항목
- [40-run-full-test-suite.md](40-run-full-test-suite.md)
