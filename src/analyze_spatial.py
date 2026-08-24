import csv
import math
import numpy as np
from sklearn.cluster import DBSCAN
import folium
from folium.plugins import HeatMap

def analyze_spatial_data():
    csv_path = "/Users/bboyamin/my_project/factchat_project/src/소상공인시장진흥공단_상가(상권)정🇧ᅩ_경🇬ᅵ_202603.csv"
    # 실제 파일명 오타 방지를 위해 기존 파일 경로 재확인
    # 한글 자소분리가 있을 수 있으므로 올바른 경로를 사용합니다.
    csv_path = "/Users/bboyamin/my_project/factchat_project/src/소상공인시장진흥공단_상가(상권)정🇧ᅩ_경🇬ᅵ_202603.csv"
    # 실제 앞선 check_commercial_data.py에서 확인한 절대 경로로 대체
    csv_path = "/Users/bboyamin/my_project/factchat_project/src/소상공인시장진흥공단_상가(상권)정보_경기_202603.csv"
    
    encoding = 'utf-8'
    
    print("1. 데이터 로드 및 필터링 중...")
    stores = []
    
    with open(csv_path, 'r', encoding=encoding) as f:
        reader = csv.reader(f)
        header = next(reader)
        
        sgg_idx = header.index('시군구명')
        large_cat_idx = header.index('상권업종대분류명')
        sub_cat_idx = header.index('상권업종중분류명')
        name_idx = header.index('상호명')
        lat_idx = header.index('위도')
        lng_idx = header.index('경도')
        dong_idx = header.index('법정동명')
        
        for row in reader:
            sgg = row[sgg_idx]
            if '용인시' in sgg:
                try:
                    lat = float(row[lat_idx])
                    lng = float(row[lng_idx])
                    # 이상 좌표 필터링
                    if 37.0 < lat < 37.5 and 127.0 < lng < 127.5:
                        stores.append({
                            'name': row[name_idx],
                            'large_cat': row[large_cat_idx],
                            'sub_cat': row[sub_cat_idx],
                            'gu': sgg,
                            'dong': row[dong_idx],
                            'lat': lat,
                            'lng': lng
                        })
                except ValueError:
                    continue
                    
    total_stores = len(stores)
    print(f"로드 완료: 용인시 유효 점포 {total_stores:,}개")
    
    # -------------------------------------------------------------
    # 2. DBSCAN 클러스터링을 통한 밀집 상권 (핫스팟) 도출
    # -------------------------------------------------------------
    print("2. DBSCAN 공간 클러스터링 계산 중 (반경 100m 이내 80개 이상 밀집)...")
    
    # 위경도 좌표 배열 추출 (라디안 단위 변환)
    coords = np.array([[math.radians(s['lat']), math.radians(s['lng'])] for s in stores])
    
    # 하버사인 거리 계산 기준
    kms_per_radian = 6371.0
    epsilon = 0.1 / kms_per_radian  # 0.1km = 100m 반경
    
    db = DBSCAN(eps=epsilon, min_samples=80, metric='haversine')
    db.fit(coords)
    
    labels = db.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    print(f"식별된 밀집 상권 클러스터 개수: {n_clusters}개")
    
    # 클러스터별 점포 맵핑
    clusters = {}
    for i, label in enumerate(labels):
        if label == -1:
            continue
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(stores[i])
        
    # 상위 10대 핵심 핫스팟 상권 분석
    top_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    
    print("\n[용인시 5대 핵심 핫스팟 상권 분석 결과]")
    print("-" * 65)
    for rank, (cid, cl_stores) in enumerate(top_clusters[:5], 1):
        # 중심점 계산
        lats = [s['lat'] for s in cl_stores]
        lngs = [s['lng'] for s in cl_stores]
        center_lat = sum(lats) / len(lats)
        center_lng = sum(lngs) / len(lngs)
        
        # 주요 업종 파악
        cat_counts = {}
        for s in cl_stores:
            cat_counts[s['sub_cat']] = cat_counts.get(s['sub_cat'], 0) + 1
        top_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        cat_str = ", ".join([f"{c}({v}개)" for c, v in top_cats])
        
        representative_dong = cl_stores[0]['dong']
        print(f"{rank}위 핫스팟: {cl_stores[0]['gu']} {representative_dong} 일대 (밀집 점포: {len(cl_stores)}개)")
        print(f"  - 대표 업종: {cat_str}")
        print(f"  - 중심 좌표: 위도 {center_lat:.5f}, 경도 {center_lng:.5f}")
        
    # -------------------------------------------------------------
    # 3. Folium 지도 생성 및 시각화 레이어 빌드
    # -------------------------------------------------------------
    print("\n3. Folium 지도 빌드 및 레이어 결합 중...")
    
    # 용인시 중심 좌표
    yongin_center = [37.2410, 127.1770]
    m = folium.Map(location=yongin_center, zoom_start=11, tiles="OpenStreetMap")
    
    # 레이어 그룹들 생성
    heat_group = folium.FeatureGroup(name="용인시 전체 점포 열지도 (Heatmap)", show=True)
    hotspot_group = folium.FeatureGroup(name="DBSCAN 핫스팟 상권 (10대 핵심 구역)", show=True)
    suji_edu_group = folium.FeatureGroup(name="수지구 특화 업종: 교육 (학원)", show=False)
    giheung_tech_group = folium.FeatureGroup(name="기흥구 특화 업종: 과학·기술", show=False)
    cheoin_food_group = folium.FeatureGroup(name="처인구 특화 업종: 음식", show=False)
    
    # 1) Heatmap 데이터 준비 및 추가
    heat_data = [[s['lat'], s['lng']] for s in stores]
    HeatMap(heat_data, radius=12, blur=8, min_opacity=0.3).add_to(heat_group)
    heat_group.add_to(m)
    
    # 2) DBSCAN 핫스팟 상권 추가
    for rank, (cid, cl_stores) in enumerate(top_clusters, 1):
        lats = [s['lat'] for s in cl_stores]
        lngs = [s['lng'] for s in cl_stores]
        c_lat = sum(lats) / len(lats)
        c_lng = sum(lngs) / len(lngs)
        
        # 중분류 3대 분포
        cat_counts = {}
        for s in cl_stores:
            cat_counts[s['sub_cat']] = cat_counts.get(s['sub_cat'], 0) + 1
        top_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        cat_str = "<br>".join([f"  • {c}: {v}개" for c, v in top_cats])
        
        popup_html = f"""
        <div style="font-family: Arial, sans-serif; width: 220px;">
            <h4 style="margin:0 0 5px 0; color:#C0392B;"><b>🔥 {rank}위 핫스팟 상권</b></h4>
            <b>위치:</b> {cl_stores[0]['gu']} {cl_stores[0]['dong']}<br>
            <b>밀집 점포수:</b> {len(cl_stores)}개 (반경 100m)<br>
            <b>주요 구성 업종:</b><br>
            {cat_str}
        </div>
        """
        
        # 중심 서클
        folium.Circle(
            location=[c_lat, c_lng],
            radius=120, # 시각적 반경 표시 (미터)
            color="#C0392B",
            fill=True,
            fill_color="#E74C3C",
            fill_opacity=0.4,
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(hotspot_group)
        
        # 순위 마커
        folium.Marker(
            location=[c_lat, c_lng],
            icon=folium.DivIcon(html=f"""
                <div style="
                    font-family: Arial; 
                    font-weight: bold; 
                    color: white; 
                    background-color: #C0392B; 
                    width: 20px; 
                    height: 20px; 
                    border-radius: 50%; 
                    text-align: center; 
                    line-height: 20px; 
                    font-size: 11px;
                    border: 1px solid white;
                ">{rank}</div>
            """),
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(hotspot_group)
        
    hotspot_group.add_to(m)
    
    # 3) 구별 특화 업종 추가 (데이터 과부하 방지를 위해 각 구당 샘플 300개씩만 무작위 시각화)
    np.random.seed(42)
    
    # 수지구 교육 점포
    suji_edu = [s for s in stores if s['gu'] == '용인시 수지구' and s['large_cat'] == '교육']
    suji_sample = np.random.choice(suji_edu, min(len(suji_edu), 300), replace=False) if suji_edu else []
    for s in suji_sample:
        folium.CircleMarker(
            location=[s['lat'], s['lng']],
            radius=4,
            color="#27AE60",
            fill=True,
            fill_color="#2ECC71",
            fill_opacity=0.7,
            popup=f"<b>{s['name']}</b><br>{s['sub_cat']} ({s['dong']})"
        ).add_to(suji_edu_group)
    suji_edu_group.add_to(m)
    
    # 기흥구 과학기술 점포
    giheung_tech = [s for s in stores if s['gu'] == '용인시 기흥구' and s['large_cat'] == '과학·기술']
    giheung_sample = np.random.choice(giheung_tech, min(len(giheung_tech), 300), replace=False) if giheung_tech else []
    for s in giheung_sample:
        folium.CircleMarker(
            location=[s['lat'], s['lng']],
            radius=4,
            color="#2980B9",
            fill=True,
            fill_color="#3498DB",
            fill_opacity=0.7,
            popup=f"<b>{s['name']}</b><br>{s['sub_cat']} ({s['dong']})"
        ).add_to(giheung_tech_group)
    giheung_tech_group.add_to(m)
    
    # 처인구 음식 점포
    cheoin_food = [s for s in stores if s['gu'] == '용인시 처인구' and s['large_cat'] == '음식']
    cheoin_sample = np.random.choice(cheoin_food, min(len(cheoin_food), 300), replace=False) if cheoin_food else []
    for s in cheoin_sample:
        folium.CircleMarker(
            location=[s['lat'], s['lng']],
            radius=4,
            color="#D35400",
            fill=True,
            fill_color="#E67E22",
            fill_opacity=0.7,
            popup=f"<b>{s['name']}</b><br>{s['sub_cat']} ({s['dong']})"
        ).add_to(cheoin_food_group)
    cheoin_food_group.add_to(m)
    
    # 지도 제어 도구 추가 (레이어 토글용)
    folium.LayerControl(collapsed=False).add_to(m)
    
    output_html = "/Users/bboyamin/my_project/factchat_project/src/용인시_상권_공간분석_시각화.html"
    m.save(output_html)
    print(f"\n[성공] 인터랙티브 지도 파일이 저장되었습니다: {output_html}")

if __name__ == "__main__":
    analyze_spatial_data()
