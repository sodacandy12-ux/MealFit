package com.human.backend;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import com.human.backend.auth.entity.AppUser;
import com.human.backend.auth.repository.AppUserRepository;
import com.human.backend.auth.service.UserPrincipal;
import com.human.backend.facility.entity.Facility;
import com.human.backend.facility.repository.FacilityRepository;

/**
 * 시설·급식 설정과 시설 관리자 기능의 권한 범위를 실제 HTTP 요청으로 검증합니다.
 * 각 테스트는 트랜잭션 종료 시 롤백되어 Supabase와 다른 테스트 데이터에 영향을 주지 않습니다.
 */
@SpringBootTest
@org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
@Transactional
class FacilityManagerPermissionIntegrationTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private FacilityRepository facilityRepository;

    @Autowired
    private AppUserRepository appUserRepository;

    private Facility facilityA;
    private Facility facilityB;
    private AppUser managerA;
    private AppUser managerB;
    private AppUser memberA;
    private AppUser memberB;

    @BeforeEach
    void setUp() {
        facilityA = facilityRepository.save(facility("A 시설"));
        facilityB = facilityRepository.save(facility("B 시설"));

        managerA = appUserRepository.save(persistedUser("manager-a@mealfit.test", "A 관리자",
                AppUser.Role.MANAGER, facilityA));
        managerB = appUserRepository.save(persistedUser("manager-b@mealfit.test", "B 관리자",
                AppUser.Role.MANAGER, facilityB));
        memberA = appUserRepository.save(persistedUser("member-a@mealfit.test", "A 구성원",
                AppUser.Role.USER, facilityA));
        memberB = appUserRepository.save(persistedUser("member-b@mealfit.test", "B 구성원",
                AppUser.Role.USER, facilityB));
    }

    @Test
    void managerCanUpdateOwnFacilityMealSettings() throws Exception {
        // 요청에 facilityId를 넣지 않아도 인증된 관리자 소속 시설만 변경되어야 합니다.
        mockMvc.perform(patch("/api/facilities/me")
                .with(principal(managerA))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "name": "A 시설 변경",
                      "facilityType": "SCHOOL",
                      "address": "서울시 강남구",
                      "contactName": "김영양",
                      "defaultMealCount": 320,
                      "breakfastMealCount": 40,
                      "lunchMealCount": 220,
                      "dinnerMealCount": 60,
                      "targetFoodCost": 5200
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.facilityId").value(facilityA.getId()))
            .andExpect(jsonPath("$.name").value("A 시설 변경"))
            .andExpect(jsonPath("$.defaultMealCount").value(320))
            .andExpect(jsonPath("$.breakfastMealCount").value(40))
            .andExpect(jsonPath("$.lunchMealCount").value(220))
            .andExpect(jsonPath("$.dinnerMealCount").value(60))
            .andExpect(jsonPath("$.targetFoodCost").value(5200));

        // 같은 요청 뒤 다른 시설 값은 변경되지 않아 시설 간 데이터가 격리되는지도 확인합니다.
        mockMvc.perform(get("/api/facilities/me").with(principal(managerB)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.facilityId").value(facilityB.getId()))
            .andExpect(jsonPath("$.name").value("B 시설"));
    }

    @Test
    void invalidMealSettingsAreRejected() throws Exception {
        // 음수 식수와 비용은 Bean Validation에서 서비스 실행 전에 400으로 차단되어야 합니다.
        mockMvc.perform(patch("/api/facilities/me")
                .with(principal(managerA))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "name": "A 시설",
                      "facilityType": "SCHOOL",
                      "defaultMealCount": -1,
                      "breakfastMealCount": 0,
                      "lunchMealCount": 100,
                      "dinnerMealCount": 0,
                      "targetFoodCost": -100
                    }
                    """))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
    }

    @Test
    void userAndAdminCannotUpdateFacilitySettings() throws Exception {
        // 설정 수정은 ROLE_MANAGER 전용이며 로그인 여부만으로는 허용되지 않습니다.
        mockMvc.perform(patch("/api/facilities/me")
                .with(user("member").roles("USER"))
                .contentType(MediaType.APPLICATION_JSON)
                .content(validFacilityRequest()))
            .andExpect(status().isForbidden());

        // 최고 관리자는 전체 회원 관리 역할이고 개별 시설 운영자는 아니므로 같은 API를 사용할 수 없습니다.
        mockMvc.perform(patch("/api/facilities/me")
                .with(user("admin").roles("ADMIN"))
                .contentType(MediaType.APPLICATION_JSON)
                .content(validFacilityRequest()))
            .andExpect(status().isForbidden());
    }

    @Test
    void managerSeesOnlyMembersFromOwnFacility() throws Exception {
        mockMvc.perform(get("/api/manager/members").with(principal(managerA)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.length()").value(2))
            .andExpect(jsonPath("$[?(@.email == 'manager-a@mealfit.test')]").exists())
            .andExpect(jsonPath("$[?(@.email == 'member-a@mealfit.test')]").exists())
            .andExpect(jsonPath("$[?(@.email == 'member-b@mealfit.test')]").doesNotExist());
    }

    @Test
    void managerCanDisableOnlyOrdinaryUserInOwnFacility() throws Exception {
        mockMvc.perform(patch("/api/manager/members/{userId}/status", memberA.getId())
                .with(principal(managerA))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"DISABLED\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.userId").value(memberA.getId()))
            .andExpect(jsonPath("$.status").value("DISABLED"));

        // 다른 시설 사용자는 URL의 userId를 알아도 변경할 수 없습니다.
        mockMvc.perform(patch("/api/manager/members/{userId}/status", memberB.getId())
                .with(principal(managerA))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"DISABLED\"}"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value("OTHER_FACILITY_MEMBER"));

        // 같은 시설이라도 MANAGER 계정은 시설 관리자가 중지할 수 없습니다.
        mockMvc.perform(patch("/api/manager/members/{userId}/status", managerA.getId())
                .with(principal(managerA))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"DISABLED\"}"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value("MANAGER_STATUS_CHANGE_NOT_ALLOWED"));
    }

    @Test
    void nonManagerCannotUseManagerMemberApi() throws Exception {
        mockMvc.perform(get("/api/manager/members").with(user("member").roles("USER")))
            .andExpect(status().isForbidden());
        mockMvc.perform(get("/api/manager/members").with(user("admin").roles("ADMIN")))
            .andExpect(status().isForbidden());
        mockMvc.perform(get("/api/manager/members"))
            .andExpect(status().isUnauthorized());
    }

    private Facility facility(String name) {
        return new Facility(name, "SCHOOL", "서울시", "담당자",
                100, 0, 100, 0, BigDecimal.valueOf(4500));
    }

    private AppUser persistedUser(String email, String name, AppUser.Role role, Facility facility) {
        AppUser user = new AppUser(email, "test-password-hash", name);
        user.changeRole(role);
        user.assignFacility(facility);
        return user;
    }

    private org.springframework.test.web.servlet.request.RequestPostProcessor principal(AppUser user) {
        UserPrincipal principal = UserPrincipal.from(user);
        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                principal,
                null,
                List.of(new SimpleGrantedAuthority("ROLE_" + principal.role())));
        return authentication(authentication);
    }

    private String validFacilityRequest() {
        return """
                {
                  "name": "수정 시설",
                  "facilityType": "SCHOOL",
                  "defaultMealCount": 100,
                  "breakfastMealCount": 0,
                  "lunchMealCount": 100,
                  "dinnerMealCount": 0,
                  "targetFoodCost": 4500
                }
                """;
    }
}
