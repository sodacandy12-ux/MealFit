import java.math.BigDecimal; import java.io.*; import java.util.*;
public class MenuQuantityCounter {
static class MenuIngredientCostVo {
 String name; BigDecimal qty,price;
 MenuIngredientCostVo(Object... args){ name=(String)args[1];qty=(BigDecimal)args[4];price=(BigDecimal)args[5]; }
 Long getIngredientId(){return 1L;} String getIngredientName(){return name;}
 String getIngredientCategory(){return "";} Boolean getIsPrimary(){return false;}
 BigDecimal getQuantity(){return qty;} BigDecimal getStandardUnitPrice(){return price;}
 Object getPriceDate(){return null;} String getPriceSource(){return null;}
 String getMappingType(){return null;} BigDecimal getConfidenceScore(){return null;}
}
static String decode(String s){return new String(Base64.getDecoder().decode(s), java.nio.charset.StandardCharsets.UTF_8);}
public static void main(String[] args)throws Exception{
 MenuQuantityCounter obj=new MenuQuantityCounter();
 BufferedReader in=new BufferedReader(new InputStreamReader(System.in,java.nio.charset.StandardCharsets.UTF_8));
 String line; StringBuilder result=new StringBuilder();
 while((line=in.readLine())!=null){ String[] p=line.split("\t",-1);
 MenuIngredientCostVo item=new MenuIngredientCostVo(1L,decode(p[2]),"",false,new BigDecimal(p[3]),BigDecimal.ZERO,null,null,null,null);
 result.append(obj.sanitizeIngredientCost(decode(p[0]),decode(p[1]),item).getQuantity().toPlainString()).append("\n"); }
 System.out.print(result);
}
    private MenuIngredientCostVo sanitizeIngredientCost(String menuName, String menuCategory, MenuIngredientCostVo item) {
        if (item == null) return null;

        String name = (menuName != null) ? menuName.trim() : "";
        String cat = (menuCategory != null) ? menuCategory.trim() : "";
        String ingName = (item.getIngredientName() != null) ? item.getIngredientName().trim() : "";
        BigDecimal qty = (item.getQuantity() != null) ? item.getQuantity() : BigDecimal.ZERO;
        BigDecimal unitPrice = (item.getStandardUnitPrice() != null) ? item.getStandardUnitPrice() : BigDecimal.ZERO;

        boolean isDessert = isDessertOrSnack(name, cat);
        boolean isSnackOrSkewer = isSnackOrSkewerMenu(name, cat);
        boolean isNoodle = isNoodleMenu(name, cat);
        boolean isRice = isRiceMenu(name, cat);
        boolean isSoup = isSoupMenu(name, cat);
        boolean isMain = isMainMenu(name, cat);

        // 1. 면류 (메밀국수, 모밀, 소바, 잔치국수, 칼국수, 우동, 냉면, 쫄면, 파스타, 짜장, 짬뽕 등)
        if (isNoodle) {
            // 면류(메밀면, 국수, 소면, 우동면, 스파게티면, 라면 등): 1인분 기준 건면 80g / 생면 110g
            if (ingName.contains("면") || ingName.contains("국수") || ingName.contains("스파게티") || ingName.contains("파스타") || ingName.contains("메밀") || ingName.contains("당면")) {
                if (qty.compareTo(BigDecimal.valueOf(80)) > 0) {
                    qty = BigDecimal.valueOf(75.0);
                }
            } else if (ingName.contains("쯔유") || ingName.contains("장국") || ingName.contains("소스") || ingName.contains("육수")) {
                if (qty.compareTo(BigDecimal.valueOf(20)) > 0) {
                    qty = BigDecimal.valueOf(15.0);
                }
            } else if (ingName.contains("가쓰오") || ingName.contains("다시마") || ingName.contains("멸치")) {
                if (qty.compareTo(BigDecimal.valueOf(5)) > 0) {
                    qty = BigDecimal.valueOf(3.0);
                }
            } else if (ingName.contains("김") || ingName.contains("김가루") || ingName.contains("와사비") || ingName.contains("겨자")) {
                if (qty.compareTo(BigDecimal.valueOf(3)) > 0) {
                    qty = BigDecimal.valueOf(1.5);
                }
            } else if (ingName.contains("무") || ingName.contains("오이") || ingName.contains("파") || ingName.contains("대파") || ingName.contains("양파")) {
                if (qty.compareTo(BigDecimal.valueOf(25)) > 0) {
                    qty = BigDecimal.valueOf(15.0);
                }
            } else if (qty.compareTo(BigDecimal.valueOf(50)) > 0) {
                qty = BigDecimal.valueOf(30.0);
            }
        }
        // 2. 꼬치/분식/간식류 (떡꼬치, 소떡소떡, 닭꼬치, 떡볶이, 핫도그, 어묵바, 튀김류 등)
        else if (isSnackOrSkewer) {
            // 떡(가래떡, 떡볶이떡, 쌀떡 등): 1개/1인분 꼬치 기준 35g
            if (ingName.contains("떡") || ingName.contains("가래떡") || ingName.contains("떡볶이") || ingName.contains("쌀")) {
                if (qty.compareTo(BigDecimal.valueOf(40)) > 0) {
                    qty = BigDecimal.valueOf(35.0);
                }
            } else if (ingName.contains("소시지") || ingName.contains("비엔나") || ingName.contains("햄")) {
                if (qty.compareTo(BigDecimal.valueOf(40)) > 0) {
                    qty = BigDecimal.valueOf(30.0);
                }
            } else if (ingName.contains("어묵") || ingName.contains("오뎅")) {
                if (qty.compareTo(BigDecimal.valueOf(45)) > 0) {
                    qty = BigDecimal.valueOf(35.0);
                }
            } else if (ingName.contains("고추장") || ingName.contains("케첩") || ingName.contains("소스") || ingName.contains("양념")) {
                if (qty.compareTo(BigDecimal.valueOf(10)) > 0) {
                    qty = BigDecimal.valueOf(5.0);
                }
            } else if (ingName.contains("설탕") || ingName.contains("물엿") || ingName.contains("올리고당")) {
                if (qty.compareTo(BigDecimal.valueOf(8)) > 0) {
                    qty = BigDecimal.valueOf(4.0);
                }
            } else if (ingName.contains("식용유") || ingName.contains("기름")) {
                if (qty.compareTo(BigDecimal.valueOf(6)) > 0) {
                    qty = BigDecimal.valueOf(3.0);
                }
            } else if (qty.compareTo(BigDecimal.valueOf(45)) > 0) {
                qty = BigDecimal.valueOf(30.0);
            }
        }
        // 3. 디저트/떡/후식류 (백설기, 꿀떡, 인절미, 송편, 경단, 과일, 빵, 음료 등)
        else if (isDessert) {
            // 쌀가루, 멥쌀, 찹쌀, 밀가루 등 주원료: 1인분 배식량 기준 25g ~ 30g
            if (ingName.contains("쌀") || ingName.contains("가루") || ingName.contains("밀가루") || ingName.contains("전분") || ingName.contains("떡")) {
                if (qty.compareTo(BigDecimal.valueOf(35)) > 0) {
                    qty = BigDecimal.valueOf(25.0);
                }
            } else if (ingName.contains("꿀") || ingName.contains("조청") || ingName.contains("시럽") || ingName.contains("연유")) {
                if (qty.compareTo(BigDecimal.valueOf(5)) > 0) {
                    qty = BigDecimal.valueOf(3.0);
                }
            } else if (ingName.contains("깨") || ingName.contains("참깨") || ingName.contains("들깨") || ingName.contains("콩고물")) {
                if (qty.compareTo(BigDecimal.valueOf(3)) > 0) {
                    qty = BigDecimal.valueOf(2.0);
                }
            } else if (ingName.contains("설탕") || ingName.contains("물엿") || ingName.contains("당류")) {
                if (qty.compareTo(BigDecimal.valueOf(8)) > 0) {
                    qty = BigDecimal.valueOf(4.0);
                }
            } else if (qty.compareTo(BigDecimal.valueOf(35)) > 0) {
                qty = BigDecimal.valueOf(25.0);
            }
        }
        // 4. 주찬/메인 육류·생선류 (제육, 불고기, 돈까스, 닭갈비, 갈비찜, 생선구이 등)
        else if (isMain) {
            if (ingName.contains("육") || ingName.contains("고기") || ingName.contains("돼지") || ingName.contains("소고기") || ingName.contains("닭") || ingName.contains("오리") || ingName.contains("생선") || ingName.contains("갈비")) {
                if (qty.compareTo(BigDecimal.valueOf(120)) > 0) {
                    qty = BigDecimal.valueOf(100.0);
                }
            } else if (ingName.contains("양파") || ingName.contains("대파") || ingName.contains("양배추") || ingName.contains("버섯")) {
                if (qty.compareTo(BigDecimal.valueOf(40)) > 0) {
                    qty = BigDecimal.valueOf(25.0);
                }
            }
        }
        // 5. 밥류 (쌀밥, 잡곡밥 등 생쌀 투입량 75~85g)
        else if (isRice && !name.contains("볶음") && !name.contains("덮밥") && !name.contains("비빔")) {
            if (ingName.contains("쌀") || ingName.contains("현미") || ingName.contains("보리") || ingName.contains("잡곡") || ingName.contains("콩")) {
                if (qty.compareTo(BigDecimal.valueOf(90)) > 0) {
                    qty = BigDecimal.valueOf(80.0);
                }
            }
        }
        // 6. 국/찌개류 (육수용 고기/두부/채소)
        else if (isSoup) {
            if (ingName.contains("육") || ingName.contains("고기") || ingName.contains("닭") || ingName.contains("해물")) {
                if (qty.compareTo(BigDecimal.valueOf(50)) > 0) {
                    qty = BigDecimal.valueOf(30.0);
                }
            } else if (ingName.contains("두부")) {
                if (qty.compareTo(BigDecimal.valueOf(45)) > 0) {
                    qty = BigDecimal.valueOf(30.0);
                }
            }
        }

        // 7. 공통: 조미료/향신료 (소금, 후추, 참기름 등) 과다 투입량 정제
        if (ingName.contains("소금") || ingName.contains("후추") || ingName.contains("고춧가루")) {
            if (qty.compareTo(BigDecimal.valueOf(4)) > 0) {
                qty = BigDecimal.valueOf(2.0);
            }
        } else if (ingName.contains("참기름") || ingName.contains("들기름") || ingName.contains("식용유") || ingName.contains("버터")) {
            if (qty.compareTo(BigDecimal.valueOf(8)) > 0) {
                qty = BigDecimal.valueOf(3.0);
            }
        } else if (ingName.contains("간장") || ingName.contains("된장") || ingName.contains("고추장") || ingName.contains("케첩") || ingName.contains("마요네즈")) {
            if (qty.compareTo(BigDecimal.valueOf(15)) > 0) {
                qty = BigDecimal.valueOf(8.0);
            }
        }

        // 8. 1인분 기준 120g 이상으로 과도하게 적재된 단일 재료 상한 제한
        if (qty.compareTo(BigDecimal.valueOf(120)) > 0) {
            qty = BigDecimal.valueOf(90.0);
        }

        return new MenuIngredientCostVo(
                item.getIngredientId(),
                item.getIngredientName(),
                item.getIngredientCategory(),
                item.getIsPrimary(),
                qty,
                unitPrice,
                item.getPriceDate(),
                item.getPriceSource(),
                item.getMappingType(),
                item.getConfidenceScore()
        );
    }
    private boolean isNoodleMenu(String name, String category) {
        String full = (name + " " + category).toLowerCase();
        return full.contains("국수") || full.contains("메밀") || full.contains("모밀") || full.contains("소바")
                || full.contains("우동") || full.contains("냉면") || full.contains("쫄면") || full.contains("칼국수")
                || full.contains("스파게티") || full.contains("파스타") || full.contains("짜장") || full.contains("짬뽕")
                || full.contains("라면") || full.contains("라멘") || full.contains("쌀국수") || full.contains("마라탕")
                || full.contains("잡채") || full.contains("비빔면") || full.contains("누들");
    }
    private boolean isMainMenu(String name, String category) {
        String full = (name + " " + category).toLowerCase();
        return full.contains("불고기") || full.contains("제육") || full.contains("돈까스") || full.contains("돈가스")
                || full.contains("갈비") || full.contains("닭") || full.contains("치킨") || full.contains("삼겹")
                || full.contains("생선") || full.contains("스테이크") || full.contains("함박") || full.contains("탕수육")
                || full.contains("까스") || full.contains("가스") || full.contains("조림") || full.contains("구이")
                || full.contains("찜") || full.contains("볶음") || full.contains("폭립") || full.contains("너비아니");
    }
    private boolean isSnackOrSkewerMenu(String name, String category) {
        String full = (name + " " + category).toLowerCase();
        return full.contains("꼬치") || full.contains("소떡") || full.contains("떡볶이") || full.contains("라볶이")
                || full.contains("어묵") || full.contains("오뎅") || full.contains("핫도그") || full.contains("순대")
                || full.contains("튀김") || full.contains("만두") || full.contains("전") || full.contains("부침")
                || full.contains("너겟") || full.contains("핑거");
    }
    private boolean isDessertOrSnack(String name, String category) {
        String full = (name + " " + category).toLowerCase();
        return full.contains("설기") || full.contains("떡") || full.contains("경단") || full.contains("송편")
                || full.contains("약과") || full.contains("약식") || full.contains("만주") || full.contains("유과")
                || full.contains("한과") || full.contains("과일") || full.contains("사과") || full.contains("배")
                || full.contains("바나나") || full.contains("오렌지") || full.contains("귤") || full.contains("포도")
                || full.contains("수박") || full.contains("참외") || full.contains("딸기") || full.contains("키위")
                || full.contains("토마토") || full.contains("디저트") || full.contains("후식") || full.contains("빵")
                || full.contains("케이크") || full.contains("케익") || full.contains("쿠키") || full.contains("머핀")
                || full.contains("와플") || full.contains("도넛") || full.contains("파이") || full.contains("토스트")
                || full.contains("카스테라") || full.contains("푸딩") || full.contains("젤리") || full.contains("요거트")
                || full.contains("요구르트") || full.contains("아이스크림") || full.contains("주스") || full.contains("음료")
                || full.contains("식혜") || full.contains("수정과") || full.contains("에이드") || full.contains("차")
                || full.contains("우유") || full.contains("두유");
    }
    private boolean isRiceMenu(String name, String category) {
        String full = (name + " " + category).toLowerCase();
        return full.contains("밥") || full.contains("죽") || full.contains("라이스");
    }
    private boolean isSoupMenu(String name, String category) {
        String full = (name + " " + category).toLowerCase();
        return full.contains("국") || full.contains("찌개") || full.contains("탕") || full.contains("스프") || full.contains("전골");
    }
}
