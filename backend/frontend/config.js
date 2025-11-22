// API 설정
const API_CONFIG = {
    // 환경 감지: 현재 호스트가 localhost면 개발 환경, 아니면 프로덕션
    getBaseURL: function() {
        const hostname = window.location.hostname;

        // 개발 환경 (localhost 또는 127.0.0.1)
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return 'http://localhost:8000/api';
        }

        // 프로덕션 환경 (192.168.219.102 또는 기타)
        return 'http://192.168.219.102:8000/api';
    }
};
